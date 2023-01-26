import time
from datetime import datetime, timedelta

import gmail
import params
import unsubscribe
import util
from db.database import get_db
from db.models import Rule
from falcon import FalconClient


def get_mail(falcon_client, mail_id):
    mail = util.get_mail_from_cache(mail_id)
    if mail is not None:
        return mail

    mail = falcon_client.gmail.get_mail(mail_id)
    util.save_mail_to_cache(mail)
    return mail


def consolidate(falcon_client, main_query):
    query = f'in:spam'
    mails = falcon_client.gmail.list_mails(query=query, max_pages=10000)
    for index, mail in enumerate(mails, 0):
        mail_id = mail['id']
        falcon_client.gmail.move_to_trash(mail_id)

        time.sleep(0.5)


def get_labels(mail):
    return {i for i in mail.get('labelIds', [])}


def should_delete_email(mail, blacklist_rules, whitelist_rules):
    mail_processed = gmail.process_mail_dic(mail)

    sender = mail_processed['Sender']
    subject = util.clean(mail_processed['Subject'])
    text = util.clean(mail_processed['Text'])
    should_unsub = unsubscribe.has_unsub_option(mail_processed)[0]

    if sender in whitelist_rules:
        util.log(f'Skip emails from [{sender}]. Sender is part of the whitelist.')
        return False

    if 'STARRED' in get_labels(mail):
        util.log(f'Skip starred.')
        return False

    if sender in blacklist_rules:
        util.log(f'Delete since sender [{sender}] is blacklisted.')
        return True


def cleanup(email, main_query, num_days):
    util.log(f'Cleanup triggered for {email} - {main_query}.')

    db = get_db()
    blacklist_rules = {i.query for i in db.session.query(Rule).filter(Rule.type == 'blacklist').all()}
    whitelist_rules = {i.query for i in db.session.query(Rule).filter(Rule.type == 'whitelist').all()}
    label_rules = {i.query for i in db.session.query(Rule).filter(Rule.type == 'label').all()}

    falcon_client = FalconClient(email=email)

    query = main_query
    if query is None:
        query = ''

    after = datetime.now() - timedelta(days=num_days)

    query += f" after:{after.strftime('%Y/%m/%d')}"
    query += ' -in:sent'
    query.strip()

    mails = falcon_client.gmail.list_mails(query=query, max_pages=10000)

    for index, mail in enumerate(mails, 0):
        mail_id = mail['id']

        mail_full = get_mail(falcon_client, mail_id)

        move_to_trash = should_delete_email(mail_full, blacklist_rules, whitelist_rules)

        if move_to_trash:
            falcon_client.gmail.move_to_trash(mail_id)

        elif 'IMPORTANT' in get_labels(mail):
            util.log(f'Remove unnecessary IMPORTANT label.')

            falcon_client.gmail.add_remove_labels(mail_id, [], ['IMPORTANT'])

            mail_full['labelIds'].remove('IMPORTANT')

        time.sleep(0.5)

    consolidate(falcon_client, main_query)


if __name__ == '__main__':
    for em in params.emails:
        cleanup(email=em, main_query=params.emails[em], num_days=10000)
