import argparse
import getpass
import time
from datetime import datetime, timedelta

import params
import util
import actions
import labeller as labeller_mod
from db.database import get_db
from db.models import Rule
from falcon import FalconClient, iterate_gmail_messages


def lower_strip_clean(string):
    if string is None:
        return ""
    return util.clean_text(string).lower()


def evaluate_clause(clause, sender, subject, text, labels, tags, timediff, snippet):
    try:
        sender = lower_strip_clean(sender)
        sender_alias = sender.split("@")[0]
        sender_domain = sender.split("@")[1]

        labels = {i.lower() for i in labels}
        tags = {i.lower() for i in tags}

        subject = lower_strip_clean(subject)
        snippet = lower_strip_clean(snippet)
        text = lower_strip_clean(text)
        subject_snippet = f"{subject} {snippet}"
        content = f"{subject} {snippet} {text}"

        minute = 60
        hour = 60 * minute
        day = 24 * hour
        week = 7 * day
        month = 30 * day
        year = 365 * day

        locals_dict = locals()
        return eval(clause, locals_dict, {})
    except Exception as e:
        util.error(f"{sender}:[{e}]")
        return False


def get_label_names(mail_processed, label_id_to_name_mapping):
    return {label_id_to_name_mapping[i] for i in mail_processed["LabelIds"]}


def compute_tags(mail_processed):
    """Compute deterministic rule-based tags from email metadata."""
    tags = set()
    if mail_processed["Unsubscribe"] is not None:
        tags.add("unsubscribe")
    return tags


def should_delete_email(mail_processed, blacklist_rules, whitelist_rules, label_id_to_name_mapping):
    curr_time = int(time.time())

    sender = lower_strip_clean(mail_processed["Sender"])
    subject = mail_processed["Subject"]
    text = mail_processed["Text"]
    snippet = mail_processed["Snippet"]
    timediff = curr_time - int(mail_processed["DateTime"].timestamp())
    labels = get_label_names(mail_processed, label_id_to_name_mapping)
    tags = compute_tags(mail_processed)

    for q in whitelist_rules:
        if evaluate_clause(q, sender, subject, text, labels, tags, timediff, snippet):
            util.log(f"Do not delete since [{q}] evaluates to True.")
            return False

    for q in blacklist_rules:
        if evaluate_clause(q, sender, subject, text, labels, tags, timediff, snippet):
            util.log(f"Delete since [{q}] evaluates to True.")
            return True

    return False


def process_labelling(mail_processed, label_rules, add_labels, remove_labels, label_id_to_name_mapping):
    curr_time = int(time.time())

    sender = mail_processed["Sender"]
    subject = mail_processed["Subject"]
    text = mail_processed["Text"]
    snippet = mail_processed["Snippet"]
    timediff = curr_time - int(mail_processed["DateTime"].timestamp())
    labels = get_label_names(mail_processed, label_id_to_name_mapping)
    tags = compute_tags(mail_processed)

    for q, label_out, args in label_rules:
        label_out = label_out.upper().strip()
        label_op_type = label_out[0]
        label_name = label_out[1:]

        if args is None:
            args = set()
        else:
            args = set(args.split(","))

        if evaluate_clause(q, sender, subject, text, labels, tags, timediff, snippet):
            if label_op_type == "+":
                if label_name not in labels:
                    util.log(f"Add label [{label_name}] since [{q}] evaluates to True.")
                    labels.add(label_name)
                    add_labels.append(label_name)
            elif label_op_type == "-":
                if label_name in labels:
                    util.log(f"Remove label [{label_name}] since [{q}] evaluates to True.")
                    labels.remove(label_name)
                    remove_labels.append(label_name)
            else:
                raise Exception(f"Invalid rule out [{label_out}].")

            if "skip_others" in args:
                util.log("Skipping processing other labelling rules.")
                break


def apply_llm_labels(mail_processed, add_label_names, remove_label_names, label_id_to_name_mapping, config):
    """Run LLM classification and compute label additions/removals."""
    batch_labels = labeller_mod.classify_emails([mail_processed], config)
    llm_labels = batch_labels.get(mail_processed["Id"], [])

    current_labels = get_label_names(mail_processed, label_id_to_name_mapping)

    # Remove stale AI labels
    for existing_label in current_labels:
        if existing_label.startswith("AI/") and existing_label not in [
            f"AI/{l}".upper() for l in llm_labels
        ]:
            remove_label_names.append(existing_label)

    # Add new AI labels
    for label in llm_labels:
        label_upper = f"AI/{label}".upper()
        if label_upper not in current_labels:
            add_label_names.append(label_upper)


def cleanup(email, main_query, num_days, key):
    util.log(f"Cleanup triggered for {email} - {main_query}.")

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
        # Phase 1: Rule-based labelling
        add_label_names = []
        remove_label_names = []

        process_labelling(
            mail_processed, label_rules, add_label_names, remove_label_names, created_label_ids
        )

        # Phase 2: LLM labelling
        apply_llm_labels(
            mail_processed, add_label_names, remove_label_names, created_label_ids, config
        )

        # Phase 3: Apply label changes to Gmail
        actions.apply_label_changes(
            falcon_client,
            mail_id,
            mail_processed,
            add_label_names,
            remove_label_names,
            created_label_names,
            created_label_ids,
        )

        # Phase 4: Evaluate delete rules (after labels are applied)
        move_to_trash = should_delete_email(
            mail_processed, blacklist_rules, whitelist_rules, created_label_ids
        )

        if move_to_trash:
            actions.trash_email(falcon_client, mail_id)

        time.sleep(0.5)

    actions.consolidate_spam(falcon_client)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="Falcon email cleanup pipeline.")
        parser.add_argument("--days", type=int, default=2, help="Number of days of email to process.")
        parser.add_argument("--key", type=str, default=None, help="Encryption passphrase for Gmail token storage. Prompted if omitted.")
        args = parser.parse_args()

        key = args.key or getpass.getpass("Please provide secret key: ")

        util.log(f"Running cleanup on emails in last [{args.days}] days.")

        for em in list(params.emails):
            cleanup(email=em, main_query=params.emails[em], num_days=args.days, key=key)

    except Exception as exp:
        util.error(exp)
