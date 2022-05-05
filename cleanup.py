import time
from datetime import datetime, timedelta

import datareader
import gmail
import unsubscribe
from falcon import FalconClient
from util import clean


def cleanup(emails, num_days):
    for em, main_query in emails.items():
        falcon_client = FalconClient(email=em)

        query = main_query
        if query is None:
            query = ''

        after = datetime.now() - timedelta(days=num_days)

        query += f" after:{after.strftime('%Y/%m/%d')}"
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

            sender = mail_processed['Sender']
            subject = clean(mail_processed['Subject'])
            should_unsub, _ = unsubscribe.is_newsletter(mail_processed)

            is_deleted = False
            if sender in datareader.blacklist_senders:
                is_deleted = True
                print(f'Delete since sender [{sender}] is blacklisted.')
                falcon_client.gmail.move_to_trash(mail_id)
            elif should_unsub:
                is_deleted = True
                unsubscribe.unsubscribe(falcon_client, mail_processed)
                falcon_client.gmail.move_to_trash(mail_id)
            else:
                for blacklisted_subject in datareader.blacklist_subjects:
                    if subject == blacklisted_subject or subject.find(blacklisted_subject) > -1:
                        is_deleted = True
                        print(f'Delete since subject [{subject}] is blacklisted.')
                        falcon_client.gmail.move_to_trash(mail_id)
                        break

            if not is_deleted:
                falcon_client.gmail.add_remove_labels(mail_id, [], ['IMPORTANT'])

            time.sleep(0.5)

        for blacklisted in datareader.blacklist_senders:
            query = f'from:{blacklisted}'
            mails = falcon_client.gmail.list_mails(query=query, max_pages=10000)
            for index, mail in enumerate(mails, 0):
                mail_id = mail['id']
                falcon_client.gmail.move_to_trash(mail_id)

                time.sleep(0.5)

        for blacklisted in datareader.blacklist_content:
            query = main_query if main_query is not None else ''
            query += f' {blacklisted}'
            if main_query is not None:
                query += f' {main_query}'

            mails = falcon_client.gmail.list_mails(query=query, max_pages=10000)
            for index, mail in enumerate(mails, 0):
                mail_id = mail['id']
                falcon_client.gmail.move_to_trash(mail_id)

                time.sleep(0.5)

        query = f'in:spam'
        mails = falcon_client.gmail.list_mails(query=query, max_pages=10000)
        for index, mail in enumerate(mails, 0):
            mail_id = mail['id']
            falcon_client.gmail.move_to_trash(mail_id)

            time.sleep(0.5)


if __name__ == '__main__':
    cleanup(emails=datareader.emails, num_days=1)
