import json
import logging
import os
import pickle
import time
from datetime import datetime
from pprint import pprint

from ai.model import Model
from gmail import Gmail
from params import project_root_dir


class FalconClient:
    def __init__(self, email):
        self.email = email
        self.gmail = Gmail()
        self.gmail.auth(self.email, method='Desktop')

        self._labels = None

    def get_labels(self):
        if self._labels is None:
            self._labels = {i['id']: i for i in self.gmail.list_labels()['labels']}
        return self._labels

    def get_label_by_name(self, name):
        labels_by_name = {i['name']: i for i in self.get_labels().values()}
        return labels_by_name.get(name, None)

    def create_label(self, name):
        created = False
        if self.get_label_by_name(name) is None:
            try:
                label_body = {
                    'name': name,
                    'type': 'user',
                    'labelListVisibility': 'labelShow',
                    'messageListVisibility': 'show',
                    'messagesTotal': 0,
                    'threadsUnread': 0,
                    'messagesUnread': 0,
                    'threadsTotal': 0,
                    'color': {
                        "textColor": '#000000',
                        "backgroundColor": '#ffffff',
                    }
                }

                label = self.gmail.create_label(label_body)
                self._labels[label['id']] = label

                created = True
            except Exception as e:
                logging.exception(e)

        return created

    def save_mails(self, filter_q):
        start_time = datetime.now()
        base_dir = os.path.join(project_root_dir, 'data', self.email)

        # load state file
        state_file_path = os.path.join(base_dir, 'state.pickle')
        os.makedirs(os.path.dirname(state_file_path), exist_ok=True)
        state = {}
        if os.path.exists(state_file_path):
            with open(state_file_path, 'rb') as fp:
                state = pickle.load(fp)

        query = filter_q if filter_q is not None else ''
        last_modified_date = state.get('lastModifiedDate', None)
        if last_modified_date is not None:
            query += f" after:{last_modified_date.strftime('%Y/%m/%d')}"

        query = query.strip()
        print(f'Modified mail listing query [{query}]')

        # do my thing with mails
        mails = self.gmail.list_mails(query=query, max_pages=10000, include_spam_and_trash=True)
        print(f'Number of mails for [{self.email}] : [{len(mails)}].')

        for index, mail in enumerate(mails, 0):
            mail_id = mail['id']
            thread_id = mail['threadId']

            mail_path = os.path.join(base_dir, thread_id, mail_id, 'mail.json')
            if os.path.exists(mail_path):
                print(f'Skipping mail #[{index}], Id [{mail_id}], ThreadId [{thread_id}].')
                continue

            print(f'Mail #[{index}], Id [{mail_id}], ThreadId [{thread_id}].')

            mail_body = self.gmail.get_mail(mail_id)

            os.makedirs(os.path.dirname(mail_path), exist_ok=True)
            with open(mail_path, 'w') as fp:
                json.dump(mail_body, fp)

            # Avoid too many api hits
            time.sleep(0.5)

        # update state
        state['lastModifiedDate'] = start_time
        with open(state_file_path, 'wb') as fp:
            pickle.dump(state, fp)


def save():
    for em, query in emails.items():
        falcon_client = FalconClient(email=em)

        # Working on building the dataset for training
        falcon_client.save_mails(filter_q=query)


def classify_one(model, falcon_client, mail):
    """
        Some of the labels can also overlap

        Example 1 - Updates, Newsletters
        Example 2 - Updates, Invoice
        etc.

        Ideally we should not overlap spam with anything
    """

    type_to_label_map = {
        'primary': 'Primary',
        'verification': 'Verification',
        'update': 'Update',
        'spam': 'Junk',
        'transaction': 'Transaction',
        'meeting': 'Meeting',
        'newsletter': 'Newsletter',
        'invoice': 'Invoice',

        # 'delivery': 'Delivery',
        # 'travel': 'Travel',
    }

    mail_id = mail['Id']

    labels = set()

    # ------------- predict via model ----------------------------------------------------------------------------------
    mail_type, probabilities, _ = model.predict(
        unsubscribe=mail['Unsubscribe'],
        sender=mail['Sender'],
        subject=mail['Subject'],
        text=mail['Text'],
        files=mail['Files']
    )

    # ------------- put into newsletter label if unsubscribe option found ----------------------------------------------

    files = mail.get('Files', [])
    unsubscribe = mail.get('Unsubscribe', False)

    if int(unsubscribe) != 0:
        # If it has option to unsub, demote it to update if above
        if mail_type not in ['spam', 'update']:
            mail_type = 'update'

        newsletter_label = type_to_label_map['newsletter']
        falcon_client.create_label(newsletter_label)

        newsletter_label_id = falcon_client.get_label_by_name(newsletter_label)['id']

        labels.add(newsletter_label_id)

    # ------------- put into meeting label if ics (invite) file attached -----------------------------------------------

    elif 'ics' in files:
        mail_type = 'primary'

        meeting_label = type_to_label_map['meeting']
        falcon_client.create_label(meeting_label)

        meeting_label_id = falcon_client.get_label_by_name(meeting_label)['id']

        labels.add(meeting_label_id)

    # ------------- for update mail types if there's a file it's most likely an invoice --------------------------------
    elif len(files) and mail_type == 'update':
        invoice_label = type_to_label_map['invoice']
        falcon_client.create_label(invoice_label)

        invoice_label_id = falcon_client.get_label_by_name(invoice_label)['id']

        labels.add(invoice_label_id)

    # ------------- mailtype could have been updated so doing this in the end ------------------------------------------
    model_label_name = type_to_label_map.get(mail_type, None)
    if model_label_name is not None:
        falcon_client.create_label(model_label_name)
        model_label_id = falcon_client.get_label_by_name(model_label_name)['id']

        labels.add(model_label_id)

    # ------------------------------------------------------------------------------------------------------------------

    if len(labels) > 0:
        falcon_client.gmail.add_remove_labels(
            mail_id,
            label_ids_add=list(labels),
            label_ids_remove=None
        )

    return mail_type


def classify():
    model = Model(name='modelinuse')
    model.load_model()

    for em, query in emails.items():
        falcon_client = FalconClient(email=em)

        if query is None:
            query = ''

        query += ' -has:userlabels'
        query.strip()

        mails = falcon_client.gmail.list_mails(query=query, max_pages=10000)

        for index, mail in enumerate(mails, 0):
            mail_id = mail['id']
            mail_processed = falcon_client.gmail.get_mail_processed(mail_id)

            mail_type = classify_one(model, falcon_client, mail_processed)
            mail_processed['Type'] = mail_type

            print(em)
            pprint(mail_processed)

            time.sleep(0.5)


if __name__ == '__main__':
    emails = {
        'siddhant.k16@iiits.in': '-from:*@iiits.in',
        'isiddhant.k@gmail.com': None,
        'k16.siddhant@gmail.com': None
    }
    classify()
