import time
from datetime import datetime, timedelta

import data

import gmail
import unsubscribe
from falcon import FalconClient


def cleanup():
    for em, query in emails.items():
        falcon_client = FalconClient(email=em)

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
            should_unsub, _ = unsubscribe.is_newsletter(mail_processed)

            if sender in data.blacklist_senders:
                falcon_client.gmail.move_to_trash(mail_id)
            elif should_unsub:
                unsubscribe.unsubscribe(falcon_client, mail_processed)
                falcon_client.gmail.move_to_trash(mail_id)

            time.sleep(0.5)

        for blacklisted in data.blacklist_senders:
            query = f'from:{blacklisted}'
            mails = falcon_client.gmail.list_mails(query=query, max_pages=10000)
            for index, mail in enumerate(mails, 0):
                mail_id = mail['id']
                falcon_client.gmail.move_to_trash(mail_id)

        query = 'in:spam'
        mails = falcon_client.gmail.list_mails(query=query, max_pages=10000)
        for index, mail in enumerate(mails, 0):
            mail_id = mail['id']
            falcon_client.gmail.move_to_trash(mail_id)


if __name__ == '__main__':
    emails = data.emails
    num_days = 30
    cleanup()
