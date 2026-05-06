import argparse
import getpass
import time

import params
import util
import actions
import state
import labeller as labeller_mod
from db.database import get_db
from db.models import Rule
from falcon import FalconClient, iterate_gmail_messages


def should_delete_email(
    mail_processed, blacklist_rules, whitelist_rules, label_id_to_name_mapping
):
    curr_time = int(time.time())

    sender = mail_processed["Sender"]
    subject = mail_processed["Subject"]
    text = mail_processed["Text"]
    snippet = mail_processed["Snippet"]
    timediff = curr_time - int(mail_processed["DateTime"].timestamp())
    labels = labeller_mod.get_label_names(mail_processed, label_id_to_name_mapping)
    tags = labeller_mod.compute_tags(mail_processed)

    for q in whitelist_rules:
        if labeller_mod.evaluate_clause(
            q, sender, subject, text, labels, tags, timediff, snippet
        ):
            util.log(f"Do not delete since [{q}] evaluates to True.")
            return False

    for q in blacklist_rules:
        if labeller_mod.evaluate_clause(
            q, sender, subject, text, labels, tags, timediff, snippet
        ):
            util.log(f"Delete since [{q}] evaluates to True.")
            return True

    return False


def cleanup(email, main_query, num_days, key):
    util.log(f"Cleanup triggered for {email} - {main_query}.")

    incremental = num_days == 0
    if incremental:
        num_days = 1

    processed_ids = state.load_processed_ids(email) if incremental else set()

    config = labeller_mod.load_config()
    db = get_db()

    def get_query(rule_type):
        return (Rule.type.like(f"{rule_type}%")) & (
            (Rule.apply_to == "all") | (Rule.apply_to.like(f"%+({email})%"))
        )

    blacklist_rules = {
        i.query for i in db.session.query(Rule).filter(get_query("blacklist")).all()
    }
    whitelist_rules = {
        i.query for i in db.session.query(Rule).filter(get_query("whitelist")).all()
    }
    whitelist_rules.add("'starred' in labels")

    label_rules = [
        (i.query, i.type.split(":")[1], i.args)
        for i in db.session.query(Rule)
        .filter(get_query("label"))
        .order_by(Rule.order)
        .all()
    ]

    util.log(f"Blacklist: [{blacklist_rules}]")
    util.log(f"Labelling rules: [{label_rules}].")

    falcon_client = FalconClient(email=email, key=key)

    labels_info = falcon_client.gmail.list_labels()["labels"]
    created_label_names = {label["name"]: label["id"] for label in labels_info}
    created_label_ids = {label["id"]: label["name"] for label in labels_info}

    for mail_id, mail_full, mail_processed in iterate_gmail_messages(
        falcon_client, main_query, num_days
    ):
        already_processed = incremental and mail_id in processed_ids

        util.log(
            f"Processing email with id [{mail_id}] and subject [{mail_processed['Subject']}]."
        )

        if not already_processed:
            # Phase 1: Rule-based labelling
            add_labels, remove_labels = labeller_mod.rule_labeller(
                mail_processed, label_rules, created_label_ids
            )

            # Phase 2: LLM labelling
            llm_adds, llm_removes = labeller_mod.llm_labeller(
                mail_processed, config, created_label_ids
            )
            add_labels.extend(llm_adds)
            remove_labels.extend(llm_removes)

            # Phase 3: Apply label changes to Gmail
            actions.apply_label_changes(
                falcon_client,
                mail_id,
                mail_processed,
                add_labels,
                remove_labels,
                created_label_names,
                created_label_ids,
            )

            state.mark_processed(email, mail_id)

        # Phase 4: Evaluate delete rules (after labels are applied)
        if should_delete_email(
            mail_processed, blacklist_rules, whitelist_rules, created_label_ids
        ):
            actions.trash_email(falcon_client, mail_id)

        time.sleep(60)

    actions.consolidate_spam(falcon_client)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="Falcon email cleanup pipeline.")
        parser.add_argument(
            "--days", type=int, default=2, help="Number of days of email to process."
        )
        parser.add_argument(
            "--key",
            type=str,
            default=None,
            help="Encryption passphrase for Gmail token storage. Prompted if omitted.",
        )
        args = parser.parse_args()

        key = args.key or getpass.getpass("Please provide secret key: ")

        util.log(f"Running cleanup on emails in last [{args.days}] days.")

        for em in list(params.emails):
            cleanup(email=em, main_query=params.emails[em], num_days=args.days, key=key)

    except Exception as exp:
        util.error(exp)
