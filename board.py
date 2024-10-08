"""

    This is a draw-board to experiment with APIS and work flows

"""
from pprint import pprint

import params
import util
from db.database import get_db
from db.models import Rule
from falcon import FalconClient, process_gmail_dic


def query():
    falcon_client = FalconClient(email=list(params.emails.keys())[0])

    mails = falcon_client.gmail.list_mails(query='from:connect@wakefit.co.in', max_pages=1)
    for mail in mails:
        mail_id = mail['id']
        mail_full = falcon_client.gmail.get_mail(mail_id)

        util.save_mail_to_cache(mail_full)

        mail_processed = process_gmail_dic(mail_full)
        sender = mail_processed['Sender'].lower()
        unsub = mail_processed['Unsubscribe']
        htmls = mail_processed['Htmls']

        pprint(mail_processed)

        break


def write_rules():
    db = get_db()
    for row in [
        ['label:+notification', "'dear investor' in content", 'all'],
        ['label:+notification', "'dear shareholder' in content", 'all'],
        ['label:+notification', "'evoting' in content", 'all'],
        ['label:+notification', "'e-voting' in content", 'all'],
    ]:
        print('-'.join(row))
        rule = Rule(
            type=row[0],
            query=row[1],
            apply_to=row[2]
        )

        db.session.merge(rule)
        db.session.commit()


if __name__ == '__main__':
    query()
    # write_rules()
