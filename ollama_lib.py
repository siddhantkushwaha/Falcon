import json
import os
import time

import ollama

import params
import util

MODEL_NAME = 'llama3'


def get_predefined_labels():
    with open(os.path.join(params.data_dir, 'labels.txt'), 'r') as fp:
        content = fp.read()
    labels = [i.lower().strip() for i in content.split()]
    return labels


def generate_prompt(labels, sender, subject, snippet, email_content):
    with open(os.path.join(params.data_dir, 'prompt.txt'), 'r') as fp:
        content = fp.read()
    prompt = content.strip()

    labels = '\n'.join(labels)
    sender = util.clean_sender(sender)
    subject = util.clean_text(subject)
    snippet = util.clean_text(snippet)
    email_content = util.clean_text(email_content)

    prompt = prompt.replace('<labels></labels>', f'<labels>{labels}</labels>')
    prompt = prompt.replace('<sender></sender>', f'<sender>{sender}</sender>')
    prompt = prompt.replace('<subject></subject>', f'<subject>{subject}</subject>')
    prompt = prompt.replace('<snippet></snippet>', f'<snippet>{snippet}</snippet>')
    prompt = prompt.replace('<content></content>', f'<content>{email_content}</content>')

    return prompt


def parse_out(text, predefined_labels):
    start = text.find('[')
    if start >= 0:
        end = text.find(']', start)
        if end >= 0:
            text = text[start: end + 1]

    llm_labels = []
    try:
        out_list = json.loads(text)
        if not isinstance(out_list, list):
            print(f'LLM output not in correct format. [{text}], [{type(out_list)}]')
        else:
            for label in out_list:
                if label in predefined_labels or label == 'none':
                    llm_labels.append(label)
                else:
                    print(f'LLM returned label [{label}] but it is not part of predefined list.')
    except:
        print(f'Could not parse out to json array. [{text}].')

    return llm_labels


def process_dump():
    rpt = os.path.join(params.root_dir, 'dump')
    for item in os.listdir(rpt):
        if not item.endswith('.json'):
            continue

        with open(os.path.join(rpt, item), 'r') as fp:
            mail = json.load(fp)

        predefined_labels = get_predefined_labels()
        prompt = generate_prompt(
            labels=predefined_labels,
            sender=mail['Sender'],
            subject=mail['Subject'],
            snippet=mail['Snippet'],
            # email_content=mail['Text']
            email_content=''
        )

        wait_time = 2

        max_attempts = 5
        for attempt in range(max_attempts):
            text_response = ollama.generate(prompt=prompt, model=MODEL_NAME)['response']
            out_list = parse_out(text_response, predefined_labels)
            if len(out_list) > 0:
                print(f"[{mail['Subject']}] -> [{', '.join(out_list)}]")
                break
            elif attempt == max_attempts - 1:
                print(f'******************* Failed after {max_attempts} attempts ****************')
            time.sleep(wait_time)

        time.sleep(wait_time)


if __name__ == '__main__':
    process_dump()
