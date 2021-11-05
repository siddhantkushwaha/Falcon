import time
from pprint import pprint

import gmail
from ai.model import Model
from emails import email_list
from falcon import FalconClient
from util import clean

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


def save():
    for em, query in emails.items():
        falcon_client = FalconClient(email=em)

        # Working on building the dataset for training
        falcon_client.save_mails(filter_q=query)


def get_model():
    global model

    if model is None:
        model = Model(name='modelinuse')
        model.load_model()

    return model


def classify_one(model, falcon_client, mail):
    """
        Some of the labels can also overlap

        Example 1 - Updates, Newsletters
        Example 2 - Updates, Invoice
        etc.

        Ideally we should not overlap spam with anything
    """

    mail_id = mail['Id']

    labels = set()

    unsubscribe = mail.get('Unsubscribe', None)
    is_newsletter = unsubscribe is not None

    # ------------- predict via model ----------------------------------------------------------------------------------
    mail_type, probabilities, _ = model.predict(
        unsubscribe=is_newsletter,
        sender=mail['Sender'],
        subject=clean(mail['Subject']),
        text=clean(mail['Text']),
        files=mail['Files']
    )

    # ------------- put into newsletter label if unsubscribe option found ----------------------------------------------

    files = mail.get('Files', [])

    if is_newsletter:
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
    for em, query in emails.items():
        falcon_client = FalconClient(email=em)

        if query is None:
            query = ''

        query += ' -has:userlabels'
        query += ' -in:sent'
        query.strip()

        mails = falcon_client.gmail.list_mails(query=query, max_pages=10000)

        for index, mail in enumerate(mails, 0):
            mail_id = mail['id']

            mail_full = falcon_client.gmail.get_mail(mail_id)

            # we added a query but keeping this for safety
            if 'SENT' in mail_full.get('labelIds', []):
                print('Skip sent mail.')
                continue

            mail_processed = gmail.process_mail_dic(mail_full)

            mail_type = classify_one(get_model(), falcon_client, mail_processed)
            mail_processed['Type'] = mail_type

            # mark spam messages read
            if mail_type == 'spam':
                falcon_client.gmail.add_remove_labels(mail_id, label_ids_add=None, label_ids_remove=['UNREAD'])

            print(em)
            pprint(mail_processed)

            time.sleep(0.5)


if __name__ == '__main__':
    emails = email_list
    classify()
