import os
import time

import yaml

from llm import get_llm_client
from llm.base import LLMClient
import util
from params import root_dir, config_dir


def load_config() -> dict:
    with open(os.path.join(config_dir, "config.yaml"), "r") as f:
        return yaml.safe_load(f)


# --- Shared helpers ---


def lower_strip_clean(string):
    if string is None:
        return ""
    return util.clean_text(string).lower()


def get_label_names(mail_processed, label_id_to_name_mapping):
    return {label_id_to_name_mapping[i] for i in mail_processed["LabelIds"]}


def compute_tags(mail_processed):
    tags = set()
    if mail_processed["Unsubscribe"] is not None:
        tags.add("unsubscribe")
    return tags


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


# --- Rule labeller ---


def rule_labeller(
    mail_processed, label_rules, label_id_to_name_mapping
) -> tuple[list, list]:
    """Apply rule-based label operations. Returns (add_label_names, remove_label_names)."""
    curr_time = int(time.time())

    sender = mail_processed["Sender"]
    subject = mail_processed["Subject"]
    text = mail_processed["Text"]
    snippet = mail_processed["Snippet"]
    timediff = curr_time - int(mail_processed["DateTime"].timestamp())
    labels = get_label_names(mail_processed, label_id_to_name_mapping)
    tags = compute_tags(mail_processed)

    add_labels = []
    remove_labels = []

    for q, label_out, args in label_rules:
        label_out = label_out.upper().strip()
        label_op_type = label_out[0]
        label_name = label_out[1:]

        args = set(args.split(",")) if args else set()

        if evaluate_clause(q, sender, subject, text, labels, tags, timediff, snippet):
            if label_op_type == "+":
                if label_name not in labels:
                    util.log(f"Add label [{label_name}] since [{q}] evaluates to True.")
                    labels.add(label_name)
                    add_labels.append(label_name)
            elif label_op_type == "-":
                if label_name in labels:
                    util.log(
                        f"Remove label [{label_name}] since [{q}] evaluates to True."
                    )
                    labels.remove(label_name)
                    remove_labels.append(label_name)
            else:
                raise Exception(f"Invalid rule out [{label_out}].")

            if "skip_others" in args:
                util.log("Skipping processing other labelling rules.")
                break

    return add_labels, remove_labels


# --- LLM labeller ---


def _load_taxonomy(taxonomy_path: str) -> dict:
    with open(os.path.join(root_dir, taxonomy_path), "r") as f:
        return yaml.safe_load(f)


def _format_taxonomy_for_prompt(taxonomy: dict) -> str:
    lines = []
    for name, meta in taxonomy["labels"].items():
        desc = meta.get("description", "")
        lines.append(f"- {name}: {desc}")
    return "\n".join(lines)


def _prepare_email_context(mail_processed: dict, body_max_chars: int) -> dict:
    body = util.clean_text(mail_processed.get("Text")) or ""
    if len(body) > body_max_chars:
        body = body[:body_max_chars] + "..."

    return {
        "id": mail_processed["Id"],
        "sender": mail_processed.get("Sender", ""),
        "subject": mail_processed.get("Subject", ""),
        "snippet": mail_processed.get("Snippet", ""),
        "body": body,
    }


def _format_emails_for_prompt(email_contexts: list[dict]) -> str:
    lines = []
    for i, ctx in enumerate(email_contexts, 1):
        lines.append(f"### Email {i} (id: {ctx['id']})")
        lines.append(f"From: {ctx['sender']}")
        lines.append(f"Subject: {ctx['subject']}")
        lines.append(f"Snippet: {ctx['snippet']}")
        if ctx["body"]:
            lines.append(f"Body: {ctx['body']}")
        lines.append("")
    return "\n".join(lines)


def _validate_labels(labels: list[str], valid_labels: set[str]) -> list[str]:
    result = []
    has_non_none = False
    for label in labels:
        normalized = label.strip().lower()
        if normalized == "none":
            continue
        has_non_none = True
        if normalized in valid_labels:
            result.append(normalized)
        else:
            util.log(f"LLM returned invalid label [{label}], dropping.")
    if has_non_none and not result:
        raise ValueError(f"all labels invalid: {labels}")
    return result


def _classify_batch(
    client: LLMClient,
    prompt_template: str,
    taxonomy_str: str,
    email_contexts: list[dict],
    valid_labels: set[str],
    max_retries: int,
    retry_delay: float,
) -> dict[str, list[str]]:
    emails_str = _format_emails_for_prompt(email_contexts)
    prompt = prompt_template.format(taxonomy=taxonomy_str, emails=emails_str)

    last_error = "unknown error"
    for attempt in range(1, max_retries + 1):
        try:
            result = client.generate_json(prompt)

            if result is None:
                last_error = "JSON parse failure (result is None)"
                raise ValueError(last_error)

            if not isinstance(result, list):
                last_error = f"expected list, got {type(result).__name__}"
                raise ValueError(last_error)

            labels_map = {}
            for item in result:
                if (
                    not isinstance(item, dict)
                    or "id" not in item
                    or "labels" not in item
                ):
                    last_error = f"malformed item in result: {item}"
                    raise ValueError(last_error)
                raw_labels = item["labels"] if isinstance(item["labels"], list) else []
                try:
                    validated = _validate_labels(raw_labels, valid_labels)
                except ValueError:
                    last_error = (
                        f"all labels invalid for email [{item['id']}]: {raw_labels}"
                    )
                    raise ValueError(last_error)
                reason = item.get("reason", "")
                labels_map[item["id"]] = (validated, reason)

            for ctx in email_contexts:
                if ctx["id"] not in labels_map:
                    labels_map[ctx["id"]] = ([], "")

            return labels_map

        except Exception as e:
            last_error = str(e)
            util.error(
                f"LLM batch attempt {attempt}/{max_retries} failed: {last_error}"
            )
            if attempt < max_retries:
                time.sleep(retry_delay * attempt)

    raise RuntimeError(f"LLM batch failed after {max_retries} attempts: {last_error}")


def _classify_emails(
    mails_processed: list[dict], config: dict
) -> dict[str, tuple[list[str], str]]:
    llm_config = config["llm"]
    labelling_config = config["labelling"]

    client = get_llm_client(llm_config)
    batch_size = llm_config["batch_size"]
    body_max_chars = llm_config["body_max_chars"]
    max_retries = llm_config.get("max_retries", 3)
    retry_delay = float(llm_config.get("retry_delay", 2.0))

    taxonomy = _load_taxonomy(labelling_config["taxonomy_file"])
    taxonomy_str = _format_taxonomy_for_prompt(taxonomy)

    valid_labels = set(taxonomy["labels"].keys())

    prompt_path = os.path.join(root_dir, labelling_config["prompt_file"])
    with open(prompt_path, "r") as f:
        prompt_template = f.read()

    email_contexts = [
        _prepare_email_context(m, body_max_chars) for m in mails_processed
    ]

    all_labels = {}
    for i in range(0, len(email_contexts), batch_size):
        batch = email_contexts[i : i + batch_size]
        all_labels.update(
            _classify_batch(
                client,
                prompt_template,
                taxonomy_str,
                batch,
                valid_labels,
                max_retries,
                retry_delay,
            )
        )

    return all_labels


def llm_labeller(mail_processed, config, label_id_to_name_mapping) -> tuple[list, list]:
    """Run LLM classification and return (add_label_names, remove_label_names) for AI/* labels."""
    batch_labels = _classify_emails([mail_processed], config)
    llm_labels, reason = batch_labels.get(mail_processed["Id"], ([], ""))

    if llm_labels:
        util.log(f"LLM labels for [{mail_processed['Id']}]: {llm_labels} — {reason}")

    current_labels = get_label_names(mail_processed, label_id_to_name_mapping)
    expected_ai_labels = {f"AI/{l}".upper() for l in llm_labels}

    add_labels = []
    remove_labels = []

    for existing in current_labels:
        if existing.startswith("AI/") and existing not in expected_ai_labels:
            remove_labels.append(existing)

    for label_upper in expected_ai_labels:
        if label_upper not in current_labels:
            add_labels.append(label_upper)

    return add_labels, remove_labels
