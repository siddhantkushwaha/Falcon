from util import clean


def is_newsletter(mail):
    unsubscribe_val = mail.get('Unsubscribe', None)
    return unsubscribe_val is not None, unsubscribe_val


def unsubscribe(falcon_client, mail_id, mail_processed):
    should_unsub, unsub_val = is_newsletter(mail_processed)
    if should_unsub:
        subject = clean(mail_processed['Subject'])
        unsub_list = mail_processed['Unsubscribe']

        unsub_list = filter(lambda y: y.startswith('mailto:'),
                            [x.strip()[1:-1] for x in unsub_list.split(', ')])
        unsub_list = list(unsub_list)

        unsub_mail = None
        unsub_subject = 'Unsubscribe'
        if len(unsub_list) > 0:
            unsub_mail = unsub_list[0].replace('mailto:', '')
            unsub_subject_idx = unsub_mail.find('?subject=')
            if unsub_subject_idx > -1:
                unsub_subject = unsub_mail[unsub_subject_idx:].replace('?subject=', '')
                unsub_mail = unsub_mail[:unsub_subject_idx]

        tag = 'Unsubscribing from email list: '
        if unsub_mail is None:
            tag = 'Cannot unsub, moving to trash: '

        print(
            tag,
            subject,
            unsub_mail,
            unsub_subject,
            sep='\n',
            end='\n------------------\n'
        )

        if unsub_mail is not None:
            try:
                falcon_client.gmail.send_to_unsubscribe(unsub_mail, unsub_subject)
            except Exception as exp:
                print('Failed to unsub.', exp)
