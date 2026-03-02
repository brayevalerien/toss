import argparse
import sys

from toss_cli.config import init_config
from toss_cli.deploy import deploy


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="toss",
        description="Deploy static sites, HTML, and Markdown to your own server.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init", help="interactive configuration setup")

    p_deploy = subparsers.add_parser("deploy", help="deploy a file or directory")
    p_deploy.add_argument("path", nargs="?", help="file or directory to deploy")
    p_deploy.add_argument("--slug", help="custom slug (default: random)")
    p_deploy.add_argument("--build", metavar="CMD", help="run a build command first")
    p_deploy.add_argument("--out", metavar="DIR", help="build output directory (with --build)")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "init":
            init_config()

        elif args.command == "deploy":
            if not args.build and not args.path:
                p_deploy.error("path is required unless --build is specified")
            url = deploy(
                path=args.path,
                slug=args.slug,
                build_cmd=args.build,
                out_dir=args.out,
            )
            print(url)

    except (FileNotFoundError, RuntimeError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
