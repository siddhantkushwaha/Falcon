import os

import yaml

from llm import get_llm_client
from llm.base import LLMClient
import util
from params import root_dir


def load_config() -> dict:
    with open(os.path.join(root_dir, "config.yaml"), "r") as f:
        return yaml.safe_load(f)


def load_taxonomy(taxonomy_path: str) -> dict:
    with open(os.path.join(root_dir, taxonomy_path), "r") as f:
        return yaml.safe_load(f)


def format_taxonomy_for_prompt(taxonomy: dict) -> str:
    lines = []
    for name, meta in taxonomy["labels"].items():
        desc = meta.get("description", "")
        lines.append(f"- {name}: {desc}")
    return "\n".join(lines)


def prepare_email_context(mail_processed: dict, body_max_chars: int) -> dict:
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


def format_emails_for_prompt(email_contexts: list[dict]) -> str:
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


def classify_batch(
    client: LLMClient,
    prompt_template: str,
    taxonomy_str: str,
    email_contexts: list[dict],
) -> dict[str, list[str]]:
    emails_str = format_emails_for_prompt(email_contexts)
    prompt = prompt_template.format(taxonomy=taxonomy_str, emails=emails_str)

    result = client.generate_json(prompt)

    labels_map = {}
    if isinstance(result, list):
        for item in result:
            if isinstance(item, dict) and "id" in item and "labels" in item:
                labels_map[item["id"]] = item["labels"]

    for ctx in email_contexts:
        if ctx["id"] not in labels_map:
            labels_map[ctx["id"]] = []

    return labels_map


def classify_emails(mails_processed: list[dict], config: dict = None) -> dict[str, list[str]]:
    """Classify emails using LLM. Returns {email_id: [labels]}."""
    if config is None:
        config = load_config()

    llm_config = config["llm"]
    labelling_config = config["labelling"]

    client = get_llm_client(llm_config)
    batch_size = llm_config.get("batch_size", 1)
    body_max_chars = llm_config.get("body_max_chars", 500)

    taxonomy = load_taxonomy(labelling_config["taxonomy_file"])
    taxonomy_str = format_taxonomy_for_prompt(taxonomy)

    prompt_path = os.path.join(root_dir, labelling_config["prompt_file"])
    with open(prompt_path, "r") as f:
        prompt_template = f.read()

    email_contexts = [
        prepare_email_context(m, body_max_chars) for m in mails_processed
    ]

    all_labels = {}
    for i in range(0, len(email_contexts), batch_size):
        batch = email_contexts[i : i + batch_size]
        batch_labels = classify_batch(client, prompt_template, taxonomy_str, batch)
        all_labels.update(batch_labels)

    return all_labels
