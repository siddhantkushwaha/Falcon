#### Rule based email processing.

###### How to set it up

- Run `pip install -r requirements.txt`
- Build the desktop_credentials.json file for GMail API.
    - Follow [these](https://gist.github.com/siddhantkushwaha/42ebc0a6d3348b0f62fb4b5e769876ed) steps to build the
      credentials.
    - Move it inside config/.
- Add emails.json inside `data/`, it should look like data/emails_templates.json
- Run `python/manage.py --update_rules` to push rules from `data/rules.csv` to SQL db.
- Run `python/cleanup.py`

###### Adding more rules to rules.csv

- The rules csv has below fields
    * `type` - If given query applies to true, this command type will be applied.
        * `blacklist` - Moved to trash.
        * `whitelist` - Falcon will skip this email.
        * `-label:<label-name>` - Given label will be removed from email.
        * `+label:<label-name>` - Given label will be added to the email.
    * `query` - A python expression.
    * `apply_to` - A coma separated list of email ids or `all`.
    * `order` - Order in which rules will be evaluated for a given email.
    * `args` - Miscellaneous arguments, coma separated.
        * `skip others` - If given rule evaluates to true, other rules will be skipped.
