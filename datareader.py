import json
import os

from params import root_dir

# ******************************* Blacklist *******************************

with open(os.path.join(root_dir, 'data', 'blacklist.json'), 'rb') as fp:
    blacklist = json.load(fp)

blacklist_senders = set()
for sender in blacklist["senders"]:
    blacklist_senders.add(sender.lower())

blacklist_subjects = []
for subject in blacklist["subject"]:
    blacklist_subjects.append(subject)

blacklist_content = []
for content in blacklist["content"]:
    blacklist_content.append(content)

# ******************************* Whitelist *******************************

with open(os.path.join(root_dir, 'data', 'whitelist.json'), 'rb') as fp:
    whitelist = json.load(fp)

whitelisted_senders = []
for sender in whitelist["senders"]:
    whitelisted_senders.append(sender.lower())

# ******************************* Emails *******************************

with open(os.path.join(root_dir, 'data', 'emails.json'), 'rb') as fp:
    emails = json.load(fp)
