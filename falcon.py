from gmail import Gmail

model = None


class FalconClient:
    def __init__(self, email):
        self.email = email
        self.gmail = Gmail()
        self.gmail.auth(self.email, method='Desktop')
