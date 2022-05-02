import json
import os.path
import pickle
import re

import numpy as np
import pandas as pd
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Embedding, Bidirectional, LSTM, Dense
from tensorflow.keras.layers.experimental.preprocessing import TextVectorization
from tensorflow.keras.models import load_model

import params
import util


class Model:

    def __init__(self, name='model'):

        self.model = None
        self.classes = None
        self.train_data = None
        self.features_ordered = None

        self.model_pt = os.path.join(params.root_dir, name)

    def __get_extensions_str(self, files):
        if files is not None:
            if type(files) is str:
                files = json.loads(files.replace('\'', "\""))
            extensions = list(filter(
                lambda x: len(x) > 0,
                map(
                    lambda x: x.split('.')[-1] if '.' in x else 'noextension',
                    files
                )
            ))
            extensions = ' '.join(extensions).lower()
        else:
            extensions = ''
        return extensions

    def __get_sender_str(self, sender):
        if sender is None:
            return ''
        sender = sender.lower()
        return ' '.join(filter(lambda x: len(x) > 0, re.split(r'[^a-z]', sender)))

    def __get_unsubscribe_str(self, unsubscribe):
        if unsubscribe is None:
            return ''
        return 'false' if int(unsubscribe) == 0 else 'true'

    def build_data(self, classes, data_path):
        self.classes = sorted(list(map(lambda l: l.lower(), classes)))

        data = pd.read_csv(data_path).replace({np.nan: None})

        items = []
        for i, row in data.iterrows():
            label = row['Type'].lower()
            if label not in self.classes:
                continue

            sender = self.__get_sender_str(row['Sender'])
            subject = util.clean(row['Subject'])
            try:
                text = util.clean(row['Text'])
            except:
                print(row)
                raise Exception
            unsubscribe = self.__get_unsubscribe_str(row['Unsubscribe'])
            extensions = self.__get_extensions_str(row['Files'])

            items.append({
                'sender': sender,
                'subject': subject,
                'text': text,
                'unsubscribe': unsubscribe,
                'extensions': extensions,
                'type': label
            })

        self.train_data = pd.DataFrame(items)
        self.train_data.to_csv(os.path.join(os.path.dirname(data_path), 'train.csv'), index=False)

    def train(
            self,
            vocab_size=None,
            split_ratio=0.9,
            num_epochs=5
    ):
        if self.classes is None:
            print('Classes list is none, did you use parse method before calling train?')
            return

        if self.train_data is None:
            print('Train dataframe is none, did you use parse method before calling train?')
            return

            # ----------- convert train df to numpy array for X and Y -----------
        train_test_data = []

        self.features_ordered = ['unsubscribe', 'extensions', 'sender', 'subject', 'text']
        for i, row in self.train_data.iterrows():

            x = ''
            for col in self.features_ordered:
                if row[col] is not None and len(row[col]) > 0:
                    x += str(row[col]).lower() + ' '
            x = x.strip()

            idx = self.classes.index(row['type'])
            if idx == -1:
                continue

            y = np.zeros(len(self.classes))
            y[idx] = 1

            train_test_data.append((x, y))

        train_test_data = np.array(train_test_data)

        # ----------- split to train x, y; test x, y-----------

        idx = int(len(train_test_data) * split_ratio)

        np.random.shuffle(train_test_data)
        train = train_test_data[:idx]
        test = train_test_data[idx:]

        train_x = np.array([i[0] for i in train])
        train_y = np.array([i[1] for i in train])

        test_x = np.array([i[0] for i in test])
        test_y = np.array([i[1] for i in test])

        # -------- build model --------
        encoder = TextVectorization(max_tokens=vocab_size)
        encoder.adapt(train_x)

        self.model = Sequential([
            encoder,
            Embedding(input_dim=len(encoder.get_vocabulary()), output_dim=64, mask_zero=True),
            Bidirectional(LSTM(64)),
            Dense(64, activation='relu'),
            Dense(len(self.classes), activation='softmax')
        ])
        self.model.compile(
            loss='categorical_crossentropy',
            optimizer='adam',
            metrics=['accuracy']
        )

        # -------- train model --------

        self.model.fit(
            x=train_x,
            y=train_y,
            batch_size=64,
            epochs=num_epochs,
            validation_data=(test_x, test_y)
        )

    def load_model(self):
        self.model = load_model(self.model_pt)

        with open(os.path.join(self.model_pt, 'classes.pickle'), 'rb') as fp:
            self.classes = pickle.load(fp)

        with open(os.path.join(self.model_pt, 'features_ordered.pickle'), 'rb') as fp:
            self.features_ordered = pickle.load(fp)

    def save_model(self):
        self.model.save(self.model_pt)

        with open(os.path.join(self.model_pt, 'classes.pickle'), 'wb') as fp:
            pickle.dump(self.classes, fp)

        with open(os.path.join(self.model_pt, 'features_ordered.pickle'), 'wb') as fp:
            pickle.dump(self.features_ordered, fp)

    def predict(self, unsubscribe, sender, subject, text, files):

        item = {
            'unsubscribe': self.__get_unsubscribe_str(unsubscribe),
            'sender': self.__get_sender_str(sender),
            'subject': util.clean(subject) if subject is not None else '',
            'text': util.clean(text) if text is not None else '',
            'extensions': self.__get_extensions_str(files)
        }

        x = ''
        for col in self.features_ordered:
            if item[col] is not None and len(item[col]) > 0:
                x += str(item[col]).lower() + ' '
        x = x.strip()

        predictions = self.model.predict(np.array([x]))[0]
        return self.classes[np.argmax(predictions)], predictions, x
