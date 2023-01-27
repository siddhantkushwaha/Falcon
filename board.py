"""

    This is a draw-board to experiment with APIS and work flows

"""
import pickle

import gmail
import params
from db.database import get_db
from db.models import Rule
from falcon import FalconClient


def query():
    falcon_client = FalconClient(email=list(params.emails.keys())[1])

    mails = falcon_client.gmail.list_mails(query='', max_pages=10000)

    senders = dict()
    with open('data/a.pickle', 'wb') as fp:
        pickle.dump(senders, fp)

    for mail in mails:
        mail_id = mail['id']
        mail_full = falcon_client.gmail.get_mail(mail_id)

        mail_processed = gmail.process_mail_dic(mail_full)
        sender = mail_processed['Sender'].lower()
        print(sender)

        senders[sender] = senders.get(sender, 0) + 1

    with open('data/a.pickle', 'wb') as fp:
        pickle.dump(senders, fp)

    senders_by_count = [(email, senders[email]) for email in senders]
    senders_by_count.sort(key=lambda x: x[1], reverse=True)
    print(senders_by_count)


def write_rules():
    db = get_db()
    for row in [
        # ['type', 'query', 'apply_to']
        # ['blacklist', "sender == 'ecatering@irctc.co.in'", 'all'],
    ]:
        rule = Rule(
            type=row[0],
            query=row[1],
            apply_to=row[2]
        )

        db.session.merge(rule)
        db.session.commit()


if __name__ == '__main__':
    write_rules()
