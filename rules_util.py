import os.path

import pandas as pd

import util
from db.database import get_db
from db.models import Rule
from params import data_dir

csv_file_path = os.path.join(data_dir, "rules.csv")


def dump_rules():
    util.log(f"Dumping rules to: [{csv_file_path}]")

    db = get_db()
    results = db.session.query(Rule).order_by(Rule.id).all()
    data = [result.__dict__ for result in results]
    for row in data:
        row.pop("_sa_instance_state", None)
    df = pd.DataFrame(data)
    df.to_csv(os.path.join(data_dir, csv_file_path), index=False)


def update_rules_from_csv():
    if not os.path.exists(csv_file_path):
        return

    util.log(f"Reading rules to: [{csv_file_path}]")

    db = get_db()
    df = pd.read_csv(csv_file_path)

    for i, row in df.iterrows():

        r_id = row["id"]
        r_type = row["type"]
        query = row["query"]
        apply_to = row["apply_to"]
        order = row["order"]
        r_args = row["args"]

        if r_args is not None and len(str(r_args).strip()) == 0:
            r_args = None

        rule_obj = db.session.query(Rule).filter_by(id=r_id).first()

        if rule_obj is None:
            rule_obj = Rule(id=r_id)

        rule_obj.type = r_type
        rule_obj.query = query
        rule_obj.apply_to = apply_to
        rule_obj.order = order
        rule_obj.args = r_args

        db.session.add(rule_obj)

    db.session.commit()
