import argparse
import sys

from toss_cli.config import init_config, load_config
from toss_cli.deploy import deploy
from toss_cli.remote import get_listings, hide_slug, undeploy_slug, unhide_slug
from toss_cli.ssh import validate_slug


def _cmd_list() -> None:
    config = load_config()
    entries = get_listings(config)
    if not entries:
        print("No deployments found.")
        return
    col = max(len(slug) for slug, _, _ in entries)
    col = max(col, 4)
    domain = config["domain"]
    print(f"{'SLUG':<{col}}  {'LINK':<{len(domain) + col + 2}}  SIZE")
    print("-" * (col + len(domain) + col + 12))
    for slug, hidden, size in sorted(entries):
        link = "[hidden]" if hidden else f"{domain}/{slug}/"
        print(f"{slug:<{col}}  {link:<{len(domain) + col + 2}}  {size}")


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

    subparsers.add_parser("list", help="list all deployments")

    p_hide = subparsers.add_parser("hide", help="make a deployment inaccessible")
    p_hide.add_argument("slug")

    p_unhide = subparsers.add_parser("unhide", help="restore a hidden deployment")
    p_unhide.add_argument("slug")

    p_undeploy = subparsers.add_parser("undeploy", help="permanently delete a deployment")
    p_undeploy.add_argument("slug")

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
            url = deploy(path=args.path, slug=args.slug, build_cmd=args.build, out_dir=args.out)
            print(url)

        elif args.command == "list":
            _cmd_list()

        elif args.command == "hide":
            validate_slug(args.slug)
            hide_slug(load_config(), args.slug)
            print(f"Hidden: {args.slug}")

        elif args.command == "unhide":
            validate_slug(args.slug)
            unhide_slug(load_config(), args.slug)
            print(f"Restored: {args.slug}")

        elif args.command == "undeploy":
            validate_slug(args.slug)
            answer = input(f"Permanently delete '{args.slug}'? [y/N] ").strip().lower()
            if answer != "y":
                print("Cancelled.")
                return
            undeploy_slug(load_config(), args.slug)
            print(f"Deleted: {args.slug}")

    except (FileNotFoundError, RuntimeError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
