import re


def clean(text):
    if text is None:
        return ''

    clean_text = []
    checklist = {'@', '.', '/', '\\'}
    for word in text.split(' '):
        if any(ch.isdigit() or ch in checklist for ch in word):
            clean_text.append('0')
        else:
            clean_text.append(word)

    text = ' '.join(clean_text)

    cleaned = re.sub(r'[^A-Za-z0-9 ]', ' ', text)
    cleaned = re.sub(r'[\s]+', ' ', cleaned)  # remove extra whitespaces
    cleaned = cleaned.strip().lower()

    return cleaned


def get_key(obj, keys, if_none_val=None):
    for key in keys:
        if obj is None:
            break
        obj = obj.get(key, None)

    if obj is None and if_none_val is not None:
        obj = if_none_val

    return obj


def set_key(obj, keys, val):
    if obj is None:
        raise Exception('Root object cannot be none for inplace op.')

    for key in keys[:-1]:
        child = obj.get(key, None)
        if child is None:
            child = {}
            obj[key] = child
        obj = child

    obj[keys[-1]] = val
