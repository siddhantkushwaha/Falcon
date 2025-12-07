"""
Fetch emails with statement label, parse out info from attached PDFs
Logic abstracted away in indian_cc_statements module, improvements will slowly be made in that module.
"""

import os
import json
import pandas as pd

from falcon import FalconClient, iterate_gmail_messages
from indian_cc_statements.parser import extract
from indian_cc_statements.cli import print_df


def main(email, key, passwords):
    falcon_client = FalconClient(email=email, key=key)
    for mail_id, mail_full, mail_processed in iterate_gmail_messages(
        falcon_client, "label:statement", 10000
    ):
        print(f"Mail ID: {mail_id}")

        if len(mail_processed["AttachmentIds"]) == 0:
            continue

        file_name = f"statement_{mail_id}.pdf"
        attachment_id = mail_processed["AttachmentIds"][0]
        attachment_path = falcon_client.gmail.download_attachment(
            mail_id, attachment_id, "data/downloads", file_name
        )

        transactions = extract(
            pdf_path=attachment_path, passwords=passwords, temp_dir="data/temp"
        )

        if len(transactions) == 0:
            continue

        data_dir = os.path.join("data", "statement_summaries", mail_id)
        os.makedirs(data_dir, exist_ok=True)

        # Save consolidated results as json
        with open(os.path.join(data_dir, "summary.json"), "w") as f:
            json.dump(transactions, f, indent=4)

        # Save consolidated results as csv
        df = pd.DataFrame(transactions)
        df.to_csv(os.path.join(data_dir, "summary.csv"), index=False)

        df = pd.DataFrame(transactions)
        print_df(df)


if __name__ == "__main__":
    main(email="", key="", passwords=[])
