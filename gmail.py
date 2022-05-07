import base64
import os.path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from queue import Queue

from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import params
from params import root_dir
from util import get_key


def process_mail_dic(mail):
    mail_id = mail['id']

    sender = None
    subject = None
    text = None
    unsubscribe_option = None
    files = []
    attachment_ids = []

    for part in mail['payloads']:

        for header in part.get('headers', []):
            header_name = header['name'].lower()
            header_value = header['value']

            # Get sender email
            if header_name == 'from':
                sender = header_value.split(' ')[-1].strip('<>')

            elif header_name == 'subject':
                subject = header_value

            elif header_name == 'list-unsubscribe':
                unsubscribe_option = header_value

        mime_type = get_key(part, ['mimeType'])
        data = get_key(part, ['body', 'data'])
        attachment_id = get_key(part, ['body', 'attachmentId'])
        filename = get_key(part, ['filename'], '')

        if len(filename) > 0:
            files.append(filename)
            attachment_ids.append(attachment_id)
            continue

        if data is None:
            continue

        data = base64.urlsafe_b64decode(data).decode()
        # with open('data/m.html', 'w') as fp:
        #     fp.write(data)

        if 'html' in mime_type:
            # prefer text from html over text from html
            soup = BeautifulSoup(data, 'lxml')
            text = soup.text

            # double check in html content to see if something's found
            if unsubscribe_option is None:
                checklist = ['opt-out', 'unsubscribe', 'edit your notification settings']
                for link in soup.find_all('a', href=True):
                    link_text = link.text.strip().lower()
                    if any(item in link_text for item in checklist):
                        unsubscribe_option = link['href']
                        break

        elif mime_type == 'text/plain':
            if text is None:
                text = data
        else:
            print(f'Unseen mime-type found [{mime_type}].')

    processed_data = {
        'Id': str(mail_id),
        'Sender': sender,
        'Subject': subject,
        'Text': text,
        'Unsubscribe': unsubscribe_option,
        'Files': files,
        'AttachmentIds': attachment_ids
    }

    return processed_data


class Gmail:

    def __init__(self):

        self.scopes = [
            'https://www.googleapis.com/auth/userinfo.email',
            'https://mail.google.com/'
        ]

        self.authenticated_email = None
        self.credentials = None

        self.__gmail_service = None
        self.__userinfo_service = None

    @property
    def gmail_service(self):
        if self.__gmail_service is None:
            self.__gmail_service = build('gmail', 'v1', credentials=self.credentials)
        return self.__gmail_service

    @property
    def userinfo_service(self):
        if self.__userinfo_service is None:
            self.__userinfo_service = build('oauth2', 'v2', credentials=self.credentials)
        return self.__userinfo_service

    # authentication method for desktop clients
    def __desktop_auth(self, email='*'):
        tokens_path = os.path.join(root_dir, f'tokens/{email}.json')

        desktop_credentials_path = os.path.join(root_dir, 'config', 'desktop_credentials.json')

        self.credentials = None
        # if token already exists
        if os.path.exists(tokens_path):
            self.credentials = Credentials.from_authorized_user_file(tokens_path, self.scopes)
        # if not exists or invalid
        if not self.credentials or not self.credentials.valid:
            # init auth flow
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(desktop_credentials_path, self.scopes)
                self.credentials = flow.run_local_server(port=0)

        self.authenticated_email = self.get_email()
        if email != self.authenticated_email:

            if os.path.exists(tokens_path):
                # clear the tokens since they most likely tinkered with
                os.remove(tokens_path)

            raise Exception(
                f'Requested email [{email}] does not match authenticated email [{self.authenticated_email}].')
        else:
            tokens_path = os.path.join(root_dir, f'tokens/{self.authenticated_email}.json')
            os.makedirs(os.path.dirname(tokens_path), exist_ok=True)
            with open(tokens_path, 'w') as token:
                token.write(self.credentials.to_json())

    # authentication method for web clients
    def __web_auth(self, email):
        raise NotImplementedError('Web authentication not implemented.')

    def auth(self, email, method='desktop'):
        # Use below setting when auth scope needs to be changed
        os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

        method = method.lower()
        if method == 'desktop':
            self.__desktop_auth(email)
        elif method == 'web':
            self.__web_auth(email)

    def get_email(self):
        return self.userinfo_service.userinfo().get().execute()['email']

    def list_labels(self):
        return self.gmail_service.users().labels().list(userId='me').execute()

    def get_label(self, label_id):
        return self.gmail_service.users().labels().get(userId='me', id=label_id).execute()

    def create_label(self, label):
        label_config = {
            'name': label,
            'type': 'user',
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show',
            'messagesTotal': 0,
            'threadsUnread': 0,
            'messagesUnread': 0,
            'threadsTotal': 0,
            'color': {
                "textColor": '#000000',
                "backgroundColor": '#ffffff',
            }
        }
        return self.gmail_service.users().labels().create(userId='me', body=label_config).execute()

    def list_mails(
            self,
            query=None,
            max_pages=1,
            include_spam_and_trash=False
    ):
        messages = []

        page_num = 1
        page_token = None
        while page_num <= max_pages and (page_num == 1 or page_token is not None):
            response = self.gmail_service.users().messages().list(
                userId='me',
                q=query,
                pageToken=page_token,
                includeSpamTrash=include_spam_and_trash
            ).execute()

            messages_by_page = response.get('messages', None)
            if messages_by_page is not None:
                messages.extend(messages_by_page)

            page_token = response.get('nextPageToken', None)
            page_num += 1

        return messages

    def get_mail(self, mail_id):
        response = self.gmail_service.users().messages().get(userId='me', id=mail_id).execute()

        payloads_queue = Queue()
        payloads_queue.put(response.pop('payload', None))

        payloads = []
        while not payloads_queue.empty():

            payload = payloads_queue.get()
            if payload is None:
                continue

            # push parts to queue for further processing
            for part in payload.pop('parts', []):
                payloads_queue.put(part)

            # this part is done
            payloads.append(payload)

        response['payloads'] = payloads
        return response

    def get_mail_processed(self, mail_id):
        mail = self.get_mail(mail_id)
        return process_mail_dic(mail)

    def add_remove_labels(self, mail_id, label_ids_add, label_ids_remove):
        return self.gmail_service.users().messages().modify(userId='me', id=mail_id, body={
            'removeLabelIds': label_ids_remove,
            'addLabelIds': label_ids_add
        }).execute()

    def send_to_unsubscribe(self, to, subject):
        text = ''
        msg = MIMEMultipart()
        msg['to'] = to
        msg['subject'] = subject
        msg.attach(MIMEText(text, 'plain'))
        raw_string = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        sent_mail = self.gmail_service.users().messages().send(
            userId='me',
            body={
                'raw': raw_string
            }
        ).execute()

        send_mail_id = sent_mail['id']
        self.move_to_trash(send_mail_id)

    def move_to_trash(self, mail_id):
        self.gmail_service.users().messages().trash(userId='me', id=mail_id).execute()

    def download_attachment(self, mail_id, attachment_id, filename=None):
        attachment = self.gmail_service.users().messages().attachments() \
            .get(userId='me', messageId=mail_id, id=attachment_id).execute()
        data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))

        if filename is not None:
            file_path = os.path.join(params.downloads_dir, mail_id, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as fp:
                fp.write(data)

            return file_path
        else:
            return data


if __name__ == '__main__':
    email = 'example@gmail.com'
    gmail = Gmail()
    gmail.auth(email, method='Desktop')
