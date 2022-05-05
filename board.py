"""

    This is a draw-board to experiment with APIS and work flows

"""

import datareader
import gmail
from falcon import FalconClient

falcon_client = FalconClient(email=list(datareader.emails.keys())[1])

mails = falcon_client.gmail.list_mails(query='Firstnaukri', max_pages=10000)
for mail in mails:
    mail_id = mail['id']
    mail_full = falcon_client.gmail.get_mail(mail_id)

    mail_processed = gmail.process_mail_dic(mail_full)
    print(mail_processed['Subject'])

    for filename, attachment_id in zip(mail_processed['Files'], mail_processed['AttachmentIds']):
        print(filename, attachment_id)

        pt = falcon_client.gmail.download_attachment(mail_id, attachment_id, filename)
        print(pt)
