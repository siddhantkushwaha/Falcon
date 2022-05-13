### "Spam is everywhere." - Siddhant Kushwaha  
  
#### Falcon is a GMail utility to automatically  
  
 - Move spam emails to trash.  
 - Move emails to trash from senders in block-list.  
 - Unsubscribe from email-lists and move to trash.  
 - Add custom queries to select emails to be moved to trash. For example   
   - 'label: category:promotions'  
   - 'from: *.@domain.com'  
 - and more.  
  
#### ToDO  
  
 - Use AI to classify emails into categories and assign labels. OTP; UPDATES; SHIPMENT; TRANSACTION etc.  
 - Perform actions based on labels. For example  
   - Delete OTP or SHIPMENT related emails older than a week.  
   - Save bills/invoice pdfs, tickets to common location for easy access.

####  Setup

 1. `pip install -r requirements.txt`
 2. Setup the template .json files for Google API, blacklist and whitelist.
 3. `python cleanup.py` or
 4. `python runcleanup.py` to run cleanup perpetually.

#### Please reach out if you feel like contributing in any of following areas

 1. Improving the ReadMe.
 2. Contributing to the email dataset for classification.
 3. Building a model for classification of emails.
 4. Rules used to detect whether an email is a news-letter.
 5. Solution to unsubscribing from email lists that provide a URL instead of an email.
 6. Other bugs or improvements.
