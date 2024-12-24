import os
import json
import time
import ollama

import params
import util

MODEL_NAME = "phi3"


def get_predefined_labels():
    with open(os.path.join(params.data_dir, "labels.txt"), "r") as fp:
        content = fp.read()
    labels = [i.lower().strip() for i in content.split()]
    return labels


def generate_prompt(labels, sender, subject, snippet, email_content):
    with open(os.path.join(params.data_dir, "prompt_no_content.txt"), "r") as fp:
        content = fp.read()

    prompt = content.strip()

    labels = "\n".join(labels)
    sender = util.clean_sender(sender)
    subject = util.clean_text(subject)
    snippet = util.clean_text(snippet)
    email_content = util.clean_text(email_content)

    prompt = prompt.replace("<labels></labels>", f"<labels>{labels}</labels>")
    prompt = prompt.replace("<sender></sender>", f"<sender>{sender}</sender>")
    prompt = prompt.replace("<subject></subject>", f"<subject>{subject}</subject>")
    prompt = prompt.replace("<snippet></snippet>", f"<snippet>{snippet}</snippet>")
    prompt = prompt.replace(
        "<content></content>", f"<content>{email_content}</content>"
    )

    return prompt


def process_email(mail, predefined_labels):
    mail_id = mail["Id"]

    prompt = generate_prompt(
        labels=predefined_labels,
        sender=mail["Sender"],
        subject=mail["Subject"],
        snippet=mail["Snippet"],
        email_content=mail["Text"],
    )

    line_str = "\n" * 2 + "*" * 100 + "\n" * 2

    attempt = 1
    max_attempts = 3
    wait_time = 5
    out_labels = []

    while attempt <= max_attempts and len(out_labels) == 0:
        if attempt > 1:
            time.sleep(wait_time)

        fp = open(os.path.join(params.dump_dir, f"{mail_id}.llm.txt"), "w")
        fp.write(prompt)
        fp.write(line_str)

        text_response = ollama.generate(prompt=prompt, model=MODEL_NAME)["response"]
        fp.write(text_response)
        fp.write(line_str)

        for predef_label in predefined_labels:
            if text_response.find(f'"{predef_label}"') > -1:
                out_labels.append(predef_label)

        if text_response.find(f'"none"') > -1:
            out_labels.append("none")

        fp.write("- ".join(out_labels))
        fp.close()

        attempt += 1

    return out_labels


def process_dump():
    predefined_labels = get_predefined_labels()
    rpt = os.path.join(params.root_dir, "dump")
    for item in os.listdir(rpt):
        if not item.endswith(".json"):
            continue

        with open(os.path.join(rpt, item), "r") as fp:
            mail = json.load(fp)

        process_email(mail, predefined_labels)


if __name__ == "__main__":
    process_dump()
