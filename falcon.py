import json
import os
import pickle
import time
from datetime import datetime

from gmail import Gmail
from params import project_root_dir


class Falcon:
    def __init__(self, email):
        self.email = email
        self.gmail = Gmail()
        self.gmail.auth(self.email, method='Desktop')

    def create_labels(self):
        """
            Creates labels required if not exists.
            (too keep things simple, create own labels instead of pre-existing labels)
        """

        labels = [
            'Primary',
            'One Time Passwords',
            'Transactions',
            'Updates',
            'Junk'
        ]

        preexisting_labels = self.gmail.list_labels()
        preexisting_label_names = set([i['name'] for i in preexisting_labels['labels']])

        for label_name in labels:
            if label_name not in preexisting_label_names:
                label_body = {
                    'name': label_name,
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
                response = self.gmail.create_label(label_body)
                print(response)

    def save_mails(self):
        start_time = datetime.now()
        base_dir = os.path.join(project_root_dir, 'data', self.email)

        # load state file
        state_file_path = os.path.join(base_dir, 'state.pickle')
        os.makedirs(os.path.dirname(state_file_path), exist_ok=True)
        state = {}
        if os.path.exists(state_file_path):
            with open(state_file_path, 'rb') as fp:
                state = pickle.load(fp)

        query = None
        last_modified_date = state.get('lastModifiedDate', None)
        if last_modified_date is not None:
            query = f"after:{last_modified_date.strftime('%Y/%m/%d')}"
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


if __name__ == '__main__':
    emails = [
        'isiddhant.k@gmail.com',
        'k16.siddhant@gmail.com',
        'siddhant.k16@iiits.in'
    ]
    for em in emails:
        falcon = Falcon(email=em)

        # Working on building the dataset for training
        falcon.save_mails()
