import time
from datetime import datetime, timedelta

import datareader
import gmail
import unsubscribe
from falcon import FalconClient
from util import clean


def is_subject_blacklisted(subject):
    for blacklisted_subject in datareader.blacklist_subjects:
        subject = subject.lower()
        blacklisted_subject = blacklisted_subject.lower()
        if subject == blacklisted_subject or subject.find(blacklisted_subject) > -1:
            return True
    return False


def is_content_blacklisted(content):
    for blacklisted_content in datareader.blacklist_content:
        content = content.lower()
        blacklisted_content = blacklisted_content.lower()
        if content == blacklisted_content or content.find(blacklisted_content) > -1:
            return True
    return False


def cleanup(email, main_query, num_days):
    print(f'Cleanup triggered for {email} - {main_query}.')
    falcon_client = FalconClient(email=email)

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
        # with open('data/m.json', 'w') as fp:
        #     fp.write(json.dumps(mail_full))

        # we added a query but keeping this for safety
        if 'SENT' in mail_full.get('labelIds', []):
            print('Skip sent mail.')
            continue

        mail_processed = gmail.process_mail_dic(mail_full)

        sender = mail_processed['Sender']
        subject = clean(mail_processed['Subject'])
        text = clean(mail_processed['Text'])
        should_unsub, _ = unsubscribe.is_newsletter(mail_processed)

        move_to_trash = True

        if sender in datareader.whitelisted_senders:
            move_to_trash = False
            print(f'Skip emails from [{sender}]. Sender is part of the whitelist.')
        elif should_unsub:
            print('Delete since this is a newsletter.')
            unsubscribe.unsubscribe(falcon_client, mail_processed)
        elif sender in datareader.blacklist_senders:
            print(f'Delete since sender [{sender}] is blacklisted.')
        elif is_subject_blacklisted(subject):
            print(f'Delete since subject [{subject}] is blacklisted.')
        elif is_content_blacklisted(text) or is_content_blacklisted(subject):
            print(f'Delete since mail content is blacklisted.')
        else:
            move_to_trash = False

        if move_to_trash:
            falcon_client.gmail.move_to_trash(mail_id)
        elif 'IMPORTANT' in mail_full.get('labelIds', []):
            print(f'Remove unnecessary IMPORTANT label.')
            falcon_client.gmail.add_remove_labels(mail_id, [], ['IMPORTANT'])

        time.sleep(0.5)

    for blacklisted_sender in datareader.blacklist_senders:
        if blacklisted_sender in datareader.whitelisted_senders:
            print(f'Skip emails from [{blacklisted_sender}]. Sender is part of the whitelist.')

        query = f'from:{blacklisted_sender}'
        mails = falcon_client.gmail.list_mails(query=query, max_pages=10000)
        for index, mail in enumerate(mails, 0):
            mail_id = mail['id']
            falcon_client.gmail.move_to_trash(mail_id)

            time.sleep(0.5)

    for blacklisted_content in datareader.blacklist_content:
        query = main_query if main_query is not None else ''
        query += f' {blacklisted_content}'

        mails = falcon_client.gmail.list_mails(query=query, max_pages=10000)
        for index, mail in enumerate(mails, 0):
            mail_id = mail['id']

            mail_full = falcon_client.gmail.get_mail(mail_id)
            # if 'SENT' in mail_full.get('labelIds', []):
            #     print('Skip sent mail.')
            #     continue

            mail_processed = gmail.process_mail_dic(mail_full)
            sender = mail_processed['Sender']
            if sender in datareader.whitelisted_senders:
                print(f'Skip emails from [{sender}]. Sender is part of the whitelist.')
                continue

            falcon_client.gmail.move_to_trash(mail_id)

            time.sleep(0.5)

    query = f'in:spam'
    mails = falcon_client.gmail.list_mails(query=query, max_pages=10000)
    for index, mail in enumerate(mails, 0):
        mail_id = mail['id']
        falcon_client.gmail.move_to_trash(mail_id)

        time.sleep(0.5)


if __name__ == '__main__':
    for em in datareader.emails:
        cleanup(email=em, main_query=datareader.emails[em], num_days=1)
