"""

    This is a draw-board to experiment with APIS and work flows

"""
import params
from db.database import get_db
from falcon import FalconClient

falcon_client = FalconClient(email=list(params.emails.keys())[0])

db = get_db()

# mails = falcon_client.gmail.list_mails(query='label:starred', max_pages=10000)
# for mail in mails:
#     mail_id = mail['id']
#     mail_full = falcon_client.gmail.get_mail(mail_id)
#
#     mail_processed = gmail.process_mail_dic(mail_full)
#     util.log(mail_processed['Subject'])
#     util.log(mail_full.get('labelIds', []))

# for blist in [
#     'no-reply@newsletter.bookmyshow.com',
#     'informations@hdfcbank.net',
#     'credit_cards@icicibank.com',
# ]:
#     rule = Rule(
#         type='blacklist',
#         query=blist.strip(),
#         apply_to='all'
#     )
#
#     db.session.merge(rule)
#     db.session.commit()
