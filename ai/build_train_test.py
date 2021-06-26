import json
import os
import re

import pandas as pd

import params

df = pd.read_csv(os.path.join(params.project_root_dir, 'dataset', 'data.csv'))

items = []

for i, row in df.iterrows():

    sender = row['Sender'].lower()
    sender = ' '.join(filter(lambda x: len(x) > 0, re.split(r'[^a-z]', sender)))

    subject = row['Subject']
    text = row['Text']

    unsubscribe = 'true' if int(row['Unsubscribe']) == 1 else 'false'

    files = row['Files']
    if files is not None:
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

    items.append({
        'sender': sender,
        'subject': subject,
        'text': text,
        'unsubscribe': unsubscribe,
        'extensions': extensions
    })

train_test_df = pd.DataFrame(items)
train_test_df.to_csv(os.path.join(params.project_root_dir, 'dataset', 'train_test.csv'), index=False)
