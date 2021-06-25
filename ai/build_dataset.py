"""
    Based on data retrieved via falcon api, build a csv for our AI model
    Input feature vector -
        a - Subject
        b - Plain text from content
        c - Has link to unsubscribe
        d - number of files attached
"""

import base64
import json
import os
import re

import pandas as pd
from bs4 import BeautifulSoup

import params
from util import get_key


def get_raw():
    for root, _, files in os.walk(os.path.join(params.project_root_dir, 'data')):
        for file in files:
            if file == 'mail.json':
                file_pt = os.path.join(root, file)
                with open(file_pt, 'r') as fp:
                    yield file_pt, json.load(fp)


def clean(text):
    clean_text = []
    checklist = {'@', '.', '/', '\\'}
    for word in text.split(' '):
        if any(ch.isdigit() or ch in checklist for ch in word):
            clean_text.append('#')
        else:
            clean_text.append(word)

    text = ' '.join(clean_text)

    cleaned = re.sub(r'[^A-Za-z0-9# ]', ' ', text)
    cleaned = re.sub(r'[\s]+', ' ', cleaned)  # remove extra whitespaces
    cleaned = cleaned.strip().lower()

    return cleaned


def process():
    counter = 0
    for pt, mail in get_raw():
        counter += 1

        mail_id = mail['id']

        parse_data_path = os.path.join(params.project_root_dir, 'parsed', f'{mail_id}.json')
        if os.path.exists(parse_data_path):
            print(f'Skipping for mail [{mail_id}].')
            continue

        sender = None
        subject = None
        text = None
        has_unsubscribe_option = False
        files = []

        for part in mail['payloads']:

            for header in part['headers']:
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

        if any(i in sender for i in ['iiits', 'isiddhant.k@gmail.com', 'k16.siddhant@gmail.com']):
            print(f'Skipping because of sender [{sender}]')
            continue

        if text is not None:
            text = clean(text)

        if subject is not None:
            subject = clean(subject)

        mail_data = {
            'Id': mail_id,
            'Sender': sender,
            'Subject': subject,
            'Text': text,
            'Unsubscribe': 1 if has_unsubscribe_option else 0,
            'Files': files,
            'Type': None
        }

        print(f'Parsed for [{mail_id}].')
        os.makedirs(os.path.dirname(parse_data_path), exist_ok=True)
        with open(parse_data_path, 'w') as fp:
            json.dump(mail_data, fp)

    print(f'Total mailed processed [{counter}].')


def build():
    pt = os.path.join(params.project_root_dir, 'dataset', 'data.csv')
    os.makedirs(os.path.dirname(pt), exist_ok=True)

    mails = dict()
    if os.path.exists(pt):
        df = pd.read_csv(pt)
        for item in df.to_dict(orient='records'):
            mails[item['Id']] = item

    for root, _, files in os.walk(os.path.join(params.project_root_dir, 'parsed')):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as fp:
                    item = json.load(fp)

                    old_item = mails.get(item['Id'], None)
                    if old_item is not None:
                        mail_type = old_item.get('Type', None)
                        if mail_type is not None:
                            item['Type'] = mail_type

                    mails[item['Id']] = item

    df = pd.DataFrame(mails.values())
    df.to_csv(os.path.join(pt), index=False)


if __name__ == '__main__':
    # -- parse data fetched from api --
    process()

    # -- build csv --
    build()
