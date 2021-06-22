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
from pprint import pprint

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
            continue
        clean_text.append(word)

    text = ' '.join(clean_text)
    text = re.sub(r'[^A-Za-z0-9]', ' ', text)
    text = re.sub(r'[\s]+', ' ', text)  # remove extra whitespaces
    text = text.strip().lower()
    return text


def process():
    for pt, mail in get_raw():

        mail_id = mail['id']

        sender = None
        subject = None
        text = None
        has_unsubscribe_option = False
        num_files = 0

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
                num_files += 1
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

        mail_data = {
            'id': mail_id,
            'sender': sender,
            'subject': subject,
            'text': text,
            'has_unsubscribe_option': 1 if has_unsubscribe_option else 0,
            'num_files': num_files
        }
        pprint(mail_data)


if __name__ == '__main__':
    process()
