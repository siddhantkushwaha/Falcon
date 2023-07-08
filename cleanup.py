import sys
import time
from datetime import datetime, timedelta

import gmail
import params
import util
from db.database import get_db
from db.models import Rule
from falcon import FalconClient


def lower_strip(string):
    if string is None:
        return ''
    return string.strip().lower()


def evaluate_clause(clause, sender, subject, text, labels, tags, timediff):
    try:
        """
            variables needed in args for eval() to work
        """

        sender = lower_strip(sender)
        sender_alias = sender.split('@')[0]
        sender_domain = sender.split('@')[1]

        labels = {i.lower() for i in labels}
        tags = {i.lower() for i in tags}

        subject = lower_strip(subject)
        text = lower_strip(text)
        content = f'{subject} {text}'

        minute = 60
        hour = 60 * minute
        day = 24 * hour
        week = 7 * day
        month = 30 * day
        year = 365 * day

        return eval(clause, {}, locals())
    except Exception as e:
        print(e, sender)
        return False


def get_mail(falcon_client, mail_id):
    return falcon_client.gmail.get_mail(mail_id)


def consolidate(falcon_client, main_query):
    query = f'in:spam'
    mails = falcon_client.gmail.list_mails(query=query, max_pages=10000)
    for index, mail in enumerate(mails, 0):
        mail_id = mail['id']
        falcon_client.gmail.move_to_trash(mail_id)

        time.sleep(0.5)


def get_label_ids(mail):
    return {i for i in mail.get('labelIds', [])}


def get_label_names(mail, label_id_to_name_mapping):
    return {label_id_to_name_mapping[i] for i in get_label_ids(mail)}


def should_delete_email(mail, blacklist_rules, whitelist_rules, label_id_to_name_mapping):
    curr_time = int(time.time())

    mail_processed = gmail.process_mail_dic(mail)
    sender = lower_strip(mail_processed['Sender'])
    subject = mail_processed['Subject']
    text = mail_processed['Text']
    timediff = curr_time - int(mail_processed['DateTime'].timestamp())
    labels = get_label_names(mail, label_id_to_name_mapping)
    tags = set()

    if mail_processed['Unsubscribe'] is not None:
        tags.add('unsubscribe')

    for q in whitelist_rules:
        if evaluate_clause(q, sender, subject, text, labels, tags, timediff):
            util.log(f'Do not delete since [{q}] evaluates to True.')
            return False

    for q in blacklist_rules:
        if evaluate_clause(q, sender, subject, text, labels, tags, timediff):
            util.log(f'Delete since [{q}] evaluates to True.')
            return True

    return False


def process_labelling(mail, label_rules, add_labels, remove_labels, label_id_to_name_mapping):
    curr_time = int(time.time())

    mail_processed = gmail.process_mail_dic(mail)
    sender = mail_processed['Sender']
    subject = mail_processed['Subject']
    text = mail_processed['Text']
    timediff = curr_time - int(mail_processed['DateTime'].timestamp())
    labels = get_label_names(mail, label_id_to_name_mapping)
    tags = set()

    if mail_processed['Unsubscribe'] is not None:
        tags.add('unsubscribe')

    for q, label_out in label_rules:
        label_out = label_out.upper().strip()

        label_op_type = label_out[0]
        label_name = label_out[1:]

        if evaluate_clause(q, sender, subject, text, labels, tags, timediff):
            if label_op_type == '+':
                if label_name not in labels:
                    util.log(f'Add label [{label_name}] since [{q}] evaluates to True.')
                    add_labels.append(label_name)
            elif label_op_type == '-':
                if label_name in labels:
                    util.log(f'Remove label [{label_name}] since [{q}] evaluates to True.')
                    remove_labels.append(label_name)
            else:
                raise Exception(f'Invalid rule out [{label_out}].')


def cleanup(email, main_query, num_days):
    util.log(f'Cleanup triggered for {email} - {main_query}.')

    db = get_db()

    def get_query(rule_type):
        return (Rule.type.like(f'{rule_type}%')) & ((Rule.apply_to == 'all') | (Rule.apply_to.like(f'%+({email})%')))

    blacklist_rules = {i.query for i in db.session.query(Rule).filter(get_query('blacklist')).all()}

    whitelist_rules = {i.query for i in db.session.query(Rule).filter(get_query('whitelist')).all()}
    whitelist_rules.add("'starred' in labels")

    label_rules = {(i.query, i.type.split(':')[1]) for i in db.session.query(Rule).filter(get_query('label')).all()}
    label_rules.add(("'important' in labels", '-IMPORTANT'))

    util.log(f'Blacklist: [{blacklist_rules}]')
    util.log(f'Labelling rules: [{label_rules}].')

    falcon_client = FalconClient(email=email)

    get_query = main_query
    if get_query is None:
        get_query = ''

    after = datetime.now() - timedelta(days=num_days)

    get_query += f" after:{after.strftime('%Y/%m/%d')}"
    get_query += ' -in:sent'
    get_query += ' -in:trash'
    get_query.strip()

    mails = falcon_client.gmail.list_mails(query=get_query, max_pages=10000)

    created_label_names = {label['name']: label['id'] for label in falcon_client.gmail.list_labels()['labels']}
    created_label_ids = {label['id']: label['name'] for label in falcon_client.gmail.list_labels()['labels']}

    for mail in mails:
        mail_id = mail['id']

        mail_full = get_mail(falcon_client, mail_id)

        move_to_trash = should_delete_email(
            mail_full,
            blacklist_rules,
            whitelist_rules,
            created_label_ids
        )

        if move_to_trash:
            falcon_client.gmail.move_to_trash(mail_id)

        else:
            add_label_names = []
            remove_label_names = []

            process_labelling(
                mail_full,
                label_rules,
                add_label_names,
                remove_label_names,
                created_label_ids
            )

            existing_label_ids = get_label_ids(mail_full)

            add_label_ids = []
            for label_name in add_label_names:
                label_id = created_label_names.get(label_name, None)
                if label_id is None:
                    util.log(f'Label [{label_name}] not found, creating it.')
                    label_id = falcon_client.gmail.create_label(label_name)['id']

                    created_label_names[label_name] = label_id
                    created_label_ids[label_id] = label_name

                add_label_ids.append(label_id)

            remove_label_ids = [created_label_names[i] for i in remove_label_names if
                                created_label_names[i] in existing_label_ids]

            if len(add_label_ids) > 0 or len(remove_label_ids) > 0:
                falcon_client.gmail.add_remove_labels(mail_id, add_label_ids, remove_label_ids)
                for label_name in remove_label_ids:
                    mail_full['labelIds'].remove(label_name)
                for label_name in add_label_ids:
                    mail_full['labelIds'].append(label_name)

        time.sleep(0.5)

    consolidate(falcon_client, main_query)


if __name__ == '__main__':
    try:
        num_days = int(sys.argv[1]) if len(sys.argv) > 1 else -1
        if num_days == -1:
            num_days = 30

        util.log(f'Running cleanup on emails in last [{num_days}] days.')

        for em in params.emails:
            cleanup(email=em, main_query=params.emails[em], num_days=num_days)

    except Exception as exp:
        util.error(exp)
        print(exp)
