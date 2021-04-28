from gmail import Gmail


class Falcon:
    def __init__(self, email):
        self.gmail = Gmail()
        self.gmail.auth(email, method='Desktop')

    def create_labels(self):
        """
            Creates labels required if not exists.
            (too keep things simple, create own labels instead of pre-existing labels)
        """

        labels = [
            'Primary',
            'One Time Passwords',
            'Transactions',
            'Updates',
            'Junk'
        ]

        preexisting_labels = self.gmail.list_labels()
        preexisting_label_names = set([i['name'] for i in preexisting_labels['labels']])

        for label_name in labels:
            if label_name not in preexisting_label_names:
                label_body = {
                    'name': label_name,
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
                response = self.gmail.create_label(label_body)
                print(response)


if __name__ == '__main__':
    falcon = Falcon(email='k16.siddhant@gmail.com')
    falcon.create_labels()
