import json
import logging
import os
import pickle
import time
from datetime import datetime

from gmail import Gmail
from params import project_root_dir

model = None


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
