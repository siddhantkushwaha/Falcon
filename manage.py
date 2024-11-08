import sys

import rules_util


def main():
    arg_to_func = {
        '--dump_rules': rules_util.dump_rules,
        '--update_rules': rules_util.update_rules_from_csv,
    }

    for arg in sys.argv[1:]:
        arg_to_func[arg]()


if __name__ == "__main__":
    main()
