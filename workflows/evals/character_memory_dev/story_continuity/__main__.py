"""Print an offline preparation packet. No URL, credentials or live mode."""

import argparse
import json

from .schedule import prepare


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare"])
    parser.parse_args()
    print(json.dumps(prepare(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
