import time
from datetime import datetime, timezone

import pytz

import datareader
import params
from cleanup import cleanup

intervals = {
    (9, 18): 15,  # in this interval check every 15 minutes
    (23, 5): 360,  # check only once in 6 hours
}


# else check every 30 minutes

def process_intervals():
    _intervals = dict()
    for interval in intervals:
        if interval[0] < interval[1]:
            _intervals[interval] = intervals[interval]
        else:
            _intervals[(interval[0], 24)] = intervals[interval]
            _intervals[(0, interval[1])] = intervals[interval]

    return _intervals


def loop():
    last_checked = datetime.fromtimestamp(0, tz=timezone.utc)
    while True:
        _intervals = process_intervals()

        curr_time = datetime.now(tz=timezone.utc)
        curr_local_time = curr_time.astimezone(pytz.timezone(params.timezone))

        timediff = int((curr_time - last_checked).total_seconds() // 60)

        time_in_minutes = (60 * curr_local_time.time().hour) + curr_local_time.time().minute

        _timediff = 30
        for interval in _intervals:
            start, end = interval[0] * 60, interval[1] * 60
            if start <= time_in_minutes <= end:
                _timediff = _intervals[interval]
                break

        formatted_time = curr_local_time.strftime('%d/%m/%y %I:%M %p')
        if timediff > _timediff:
            print(formatted_time, f'Last cleanup ran {timediff} minutes ago, triggering cleanup.')
            for em in datareader.emails:
                cleanup(email=em, main_query=datareader.emails[em], num_days=1)

            last_checked = curr_time
        else:
            print(formatted_time, f'Last cleanup ran {timediff} minutes ago, skipping cleanup.')

        time.sleep(60)


if __name__ == '__main__':
    loop()
