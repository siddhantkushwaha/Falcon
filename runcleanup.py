import time

import datareader
from cleanup import cleanup

while True:
    cleanup(emails=datareader.emails, num_days=1)
    time.sleep(1800)
