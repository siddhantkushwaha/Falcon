import json
import os

from params import root_dir

with open(os.path.join(root_dir, 'data', 'blacklist.json'), 'rb') as fp:
    blacklist = json.load(fp)

blacklist_senders = set()
for sender in blacklist["senders"]:
    blacklist_senders.add(sender)

with open(os.path.join(root_dir, 'data', 'emails.json'), 'rb') as fp:
    emails = json.load(fp)
