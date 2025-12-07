import sys

import rules_util
import util


def main():
    arg_to_func = {
        "--dump_rules": (
            rules_util.dump_rules,
            "Dumps rules from sqlite db to rules.csv.",
        ),
        "--update_rules": (
            rules_util.update_rules_from_csv,
            "Pushes rules from rules.csv to sqlite db.",
        ),
        "--dump_md": (util.rules_sample_csv_to_md, None),
    }

    if len(sys.argv) < 2:
        string_items = [
            f"{arg} - {arg_to_func[arg][1]}"
            for arg in arg_to_func
            if arg_to_func[arg][1] is not None
        ]
        args_string = "\n".join(string_items)
        print(f"Accepted args:\n{args_string}")

    for arg in sys.argv[1:]:
        if arg in arg_to_func:
            arg_to_func[arg][0]()


if __name__ == "__main__":
    main()
