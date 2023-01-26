"""

    This is a draw-board to experiment with APIS and work flows

"""

import gmail
import params
import util
from falcon import FalconClient

falcon_client = FalconClient(email=list(params.emails.keys())[0])

mails = falcon_client.gmail.list_mails(query='label:starred', max_pages=10000)
for mail in mails:
    mail_id = mail['id']
    mail_full = falcon_client.gmail.get_mail(mail_id)

    mail_processed = gmail.process_mail_dic(mail_full)
    util.log(mail_processed['Subject'])
    util.log(mail_full.get('labelIds', []))
