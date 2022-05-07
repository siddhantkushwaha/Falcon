import logging

from gmail import Gmail

model = None


class FalconClient:
    def __init__(self, email):
        self.email = email
        self.gmail = Gmail()
        self.gmail.auth(self.email, method='Desktop')

        self._labels = None

    def get_labels(self):
        if self._labels is None:
            self._labels = {i['id']: i for i in self.gmail.list_labels()['labels']}
        return self._labels

    def get_label_by_name(self, name):
        labels_by_name = {i['name']: i for i in self.get_labels().values()}
        return labels_by_name.get(name, None)

    def create_label(self, name):
        created = False
        if self.get_label_by_name(name) is None:
            try:
                label_body = {
                    'name': name,
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

                label = self.gmail.create_label(label_body)
                self._labels[label['id']] = label

                created = True
            except Exception as e:
                logging.exception(e)

        return created
