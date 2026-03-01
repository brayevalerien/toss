import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="toss",
        description="Deploy static sites, HTML, and Markdown to your own server.",
    )
    parser.add_subparsers(dest="command")
    parser.parse_args()

    print("no command — run `toss --help` for usage")
    sys.exit(1)


if __name__ == "__main__":
    main()
