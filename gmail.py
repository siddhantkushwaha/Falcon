import base64
import os.path
from queue import Queue

from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from params import project_root_dir
from util import get_key, clean


def process_mail_dic(mail):
    mail_id = mail['id']

    sender = None
    subject = None
    text = None
    has_unsubscribe_option = False
    files = []

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
                has_unsubscribe_option = True

        mime_type = get_key(part, ['mimeType'])
        data = get_key(part, ['body', 'data'])
        filename = get_key(part, ['filename'], '')

        if len(filename) > 0:
            files.append(filename)
            continue

        if data is None:
            continue

        data = base64.urlsafe_b64decode(data).decode()

        if 'html' in mime_type:
            # prefer text from html over text from html
            soup = BeautifulSoup(data, 'lxml')
            text = soup.text

            # double check in html content to see if something's found
            if not has_unsubscribe_option:
                checklist = ['opt-out', 'unsubscribe']
                for link in soup.findAll('a'):
                    link_text = link.text.strip().lower()
                    if any(item in link_text for item in checklist):
                        has_unsubscribe_option = True
                        break

        elif mime_type == 'text/plain':
            if text is None:
                text = data
        else:
            print(f'Unseen mime-type found [{mime_type}].')

    if text is not None:
        text = clean(text)

    if subject is not None:
        subject = clean(subject)

    processed_data = {
        'Id': str(mail_id),
        'Sender': sender,
        'Subject': subject,
        'Text': text,
        'Unsubscribe': 1 if has_unsubscribe_option else 0,
        'Files': files,
    }

    return processed_data


class Gmail:

    def __init__(self):

        self.scopes = [
            'https://www.googleapis.com/auth/userinfo.email',
            'https://mail.google.com/'
        ]

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
        tokens_path = os.path.join(project_root_dir, f'tokens/{email}.json')

        desktop_credentials_path = os.path.join(project_root_dir, 'config', 'desktop_credentials.json')

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

        authenticated_email = self.get_email()
        if email != authenticated_email:

            if os.path.exists(tokens_path):
                # clear the tokens since they most likely tinkered with
                os.remove(tokens_path)

            raise Exception(f'Requested email [{email}] does not match authenticated email [{authenticated_email}].')
        else:
            tokens_path = os.path.join(project_root_dir, f'tokens/{authenticated_email}.json')
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
        return self.gmail_service.users().labels().create(userId='me', body=label).execute()

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


if __name__ == '__main__':
    email = 'example@gmail.com'
    gmail = Gmail()
    gmail.auth(email, method='Desktop')
