import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from params import project_root_dir


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
