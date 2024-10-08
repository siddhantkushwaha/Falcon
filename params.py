import json
import os

root_dir = os.path.dirname(os.path.realpath(__file__))

downloads_dir = os.path.join(root_dir, 'downloads')
data_dir = os.path.join(root_dir, 'data')
config_dir = os.path.join(root_dir, 'config')
dump_dir = os.path.join(root_dir, 'dump')

timezone = 'Asia/Kolkata'

with open(os.path.join(root_dir, 'data', 'emails.json'), 'rb') as fp:
    emails = json.load(fp)
