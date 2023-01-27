"""

    This is a draw-board to experiment with APIS and work flows

"""

import gmail
import params
import util
from db.database import get_db
from db.models import Rule
from falcon import FalconClient


def query():
    falcon_client = FalconClient(email=list(params.emails.keys())[0])
    mails = falcon_client.gmail.list_mails(query='label:starred', max_pages=10000)
    for mail in mails:
        mail_id = mail['id']
        mail_full = falcon_client.gmail.get_mail(mail_id)

        mail_processed = gmail.process_mail_dic(mail_full)

        util.log(mail_processed['Subject'])
        util.log(mail_full.get('labelIds', []))


def write_rules():
    db = get_db()
    for row in [
        # ['type', 'query', 'apply_to']
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
