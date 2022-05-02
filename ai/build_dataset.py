"""
    Based on data retrieved via falcon api, build a csv for our AI model
    Input feature vector -
        a - Subject
        b - Plain text from content
        c - Has link to unsubscribe
        d - number of files attached
"""

import json
import os

import pandas as pd

import gmail
import params


def get_raw():
    for root, _, files in os.walk(os.path.join(params.root_dir, 'data')):
        for file in files:
            if file == 'mail.json':
                file_pt = os.path.join(root, file)
                with open(file_pt, 'r') as fp:
                    yield file_pt, json.load(fp)


def process():
    counter = 0
    for pt, mail in get_raw():
        counter += 1

        mail_id = mail['id']
        parse_data_path = os.path.join(params.root_dir, 'parsed', f'{mail_id}.json')
        if os.path.exists(parse_data_path):
            print(f'Skipping for mail [{mail_id}].')
            continue

        mail_data = gmail.process_mail_dic(mail)

        print(f'Parsed for [{mail_id}].')
        os.makedirs(os.path.dirname(parse_data_path), exist_ok=True)
        with open(parse_data_path, 'w') as fp:
            json.dump(mail_data, fp)

    print(f'Total mailed processed [{counter}].')


def build():
    pt = os.path.join(params.root_dir, 'dataset', 'data.csv')
    os.makedirs(os.path.dirname(pt), exist_ok=True)

    mails = dict()
    if os.path.exists(pt):
        df = pd.read_csv(pt)
        df.to_csv(os.path.join(os.path.dirname(pt), 'data_backup.csv'), index=False)

        for item in df.to_dict(orient='records'):
            mails[item['Id']] = item

    for root, _, files in os.walk(os.path.join(params.root_dir, 'parsed')):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as fp:
                    item = json.load(fp)

                    old_item = mails.get(item['Id'], {})
                    item['Type'] = old_item.get('Type', None)

                    mails[item['Id']] = item

    df = pd.DataFrame(mails.values())
    df.to_csv(pt, index=False)


if __name__ == '__main__':
    # -- parse data fetched from api --
    process()

    # -- build csv --
    build()
