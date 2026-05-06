import time

import util


def resolve_label_id(label_name, created_label_names, created_label_ids, falcon_client):
    """Resolve a label name to its Gmail ID, creating nested labels as needed."""
    prev_node = ""
    label_id = None
    for label_node in label_name.split("/"):
        if len(prev_node) > 0:
            label_node = f"{prev_node}/{label_node}"

        label_id = created_label_names.get(label_node, None)
        if label_id is None:
            util.log(f"Label [{label_node}] not found, creating it.")
            label_id = falcon_client.gmail.create_label(label_node)["id"]
            created_label_names[label_node] = label_id
            created_label_ids[label_id] = label_node

        prev_node = label_node

    return label_id


def apply_label_changes(
    falcon_client,
    mail_id,
    mail_processed,
    add_label_names,
    remove_label_names,
    created_label_names,
    created_label_ids,
):
    """Apply label additions and removals to a single email in Gmail."""
    existing_label_ids = mail_processed["LabelIds"]

    add_label_ids = []
    for label_name in add_label_names:
        label_id = resolve_label_id(
            label_name, created_label_names, created_label_ids, falcon_client
        )
        add_label_ids.append(label_id)

    remove_label_ids = [
        created_label_names[i]
        for i in remove_label_names
        if created_label_names.get(i) in existing_label_ids
    ]

    if len(add_label_ids) > 0 or len(remove_label_ids) > 0:
        falcon_client.gmail.add_remove_labels(mail_id, add_label_ids, remove_label_ids)

    return add_label_ids, remove_label_ids


def trash_email(falcon_client, mail_id):
    """Move a single email to trash."""
    falcon_client.gmail.move_to_trash(mail_id)


def consolidate_spam(falcon_client):
    """Move all spam to trash."""
    query = "in:spam"
    mails = falcon_client.gmail.list_mails(query=query, max_pages=10000)
    for mail in mails:
        falcon_client.gmail.move_to_trash(mail["id"])
        time.sleep(0.5)
