#### Rule based email processing.

###### How to set it up

- Run `pip install -r requirements.txt`
- Build the desktop_credentials.json file for GMail API.
	- Follow [these](https://gist.github.com/siddhantkushwaha/42ebc0a6d3348b0f62fb4b5e769876ed) steps to build the credentials.
	-  Move it inside config/.
- Run `python db/init.py` to initialize db.
- Add emails.json inside `data/`, it should look like data/emails_templates.json
- Run `python/cleanup.py`

*This readme does not have everything. I'll add more information soon.*
