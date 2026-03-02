import argparse
import sys

from toss_cli.config import init_config


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="toss",
        description="Deploy static sites, HTML, and Markdown to your own server.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init", help="interactive configuration setup")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "init":
            init_config()
    except (FileNotFoundError, RuntimeError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
