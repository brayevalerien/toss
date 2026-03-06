import argparse
import json
import sys

from toss_cli.config import init_config, load_config
from toss_cli.deploy import deploy
from toss_cli.remote import get_all_stats, get_listings, get_stats, hide_slug, undeploy_slug, unhide_slug
from toss_cli.ssh import validate_slug


def _cmd_list(json_output: bool = False) -> None:
    config = load_config()
    entries = get_listings(config)
    if not entries:
        if json_output:
            print("[]")
        else:
            print("No deployments found.")
        return
    slugs = [slug for slug, _, _ in entries]
    if not json_output and "log_path" in config:
        print("fetching stats...", file=sys.stderr)
    stats = get_all_stats(config, slugs)
    domain = config["domain"]

    if json_output:
        rows = []
        for slug, hidden, size in sorted(entries):
            s = (stats or {}).get(slug)
            rows.append({
                "slug": slug,
                "url": None if hidden else f"https://{domain}/{slug}/",
                "hidden": hidden,
                "size": size,
                "requests": s["total"] if s else None,
                "visitors": s["unique_ips"] if s else None,
            })
        print(json.dumps(rows))
        return

    col = max(len(slug) for slug in slugs)
    col = max(col, 4)
    link_col = len("https://") + len(domain) + col + 2
    if stats:
        print(f"{'SLUG':<{col}}  {'LINK':<{link_col}}  {'SIZE':<6}  {'REQUESTS':>8}  {'VISITORS':>8}")
        print("-" * (col + link_col + 34))
        for slug, hidden, size in sorted(entries):
            link = "[hidden]" if hidden else f"https://{domain}/{slug}/"
            s = stats.get(slug, {"total": 0, "unique_ips": 0})
            print(f"{slug:<{col}}  {link:<{link_col}}  {size:<6}  {s['total']:>8}  {s['unique_ips']:>8}")
    else:
        print(f"{'SLUG':<{col}}  {'LINK':<{link_col}}  SIZE")
        print("-" * (col + link_col + 12))
        for slug, hidden, size in sorted(entries):
            link = "[hidden]" if hidden else f"https://{domain}/{slug}/"
            print(f"{slug:<{col}}  {link:<{link_col}}  {size}")


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
    p_deploy.add_argument("-y", "--yes", action="store_true", help="skip overwrite confirmation")
    p_deploy.add_argument("--title", help="page title for Markdown deployments")
    p_deploy.add_argument("--json", action="store_true", help="output as JSON")

    p_list = subparsers.add_parser("list", help="list all deployments")
    p_list.add_argument("--json", action="store_true", help="output as JSON")

    p_hide = subparsers.add_parser("hide", help="make a deployment inaccessible")
    p_hide.add_argument("slug")
    p_hide.add_argument("--json", action="store_true", help="output as JSON")

    p_unhide = subparsers.add_parser("unhide", help="restore a hidden deployment")
    p_unhide.add_argument("slug")
    p_unhide.add_argument("--json", action="store_true", help="output as JSON")

    p_undeploy = subparsers.add_parser("undeploy", help="permanently delete a deployment")
    p_undeploy.add_argument("slug")
    p_undeploy.add_argument("-y", "--yes", action="store_true", help="skip deletion confirmation")
    p_undeploy.add_argument("--json", action="store_true", help="output as JSON")

    p_stats = subparsers.add_parser("stats", help="show visit stats for a deployment")
    p_stats.add_argument("slug")
    p_stats.add_argument("--json", action="store_true", help="output as JSON")

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
            url = deploy(path=args.path, slug=args.slug, build_cmd=args.build, out_dir=args.out, yes=args.yes, quiet=args.json, title=args.title)
            if args.json:
                slug = url.rstrip("/").rsplit("/", 1)[-1]
                print(json.dumps({"url": url, "slug": slug}))
            else:
                print(url)

        elif args.command == "list":
            _cmd_list(json_output=args.json)

        elif args.command == "hide":
            validate_slug(args.slug)
            hide_slug(load_config(), args.slug)
            if args.json:
                print(json.dumps({"slug": args.slug, "hidden": True}))
            else:
                print(f"Hidden: {args.slug}")

        elif args.command == "unhide":
            validate_slug(args.slug)
            unhide_slug(load_config(), args.slug)
            if args.json:
                print(json.dumps({"slug": args.slug, "hidden": False}))
            else:
                print(f"Restored: {args.slug}")

        elif args.command == "undeploy":
            validate_slug(args.slug)
            if not args.yes:
                answer = input(f"Permanently delete '{args.slug}'? [y/N] ").strip().lower()
                if answer != "y":
                    print("Cancelled.")
                    return
            print("deleting...", file=sys.stderr)
            undeploy_slug(load_config(), args.slug)
            if args.json:
                print(json.dumps({"slug": args.slug, "deleted": True}))
            else:
                print(f"Deleted: {args.slug}")

        elif args.command == "stats":
            validate_slug(args.slug)
            config = load_config()
            if "log_path" not in config:
                if args.json:
                    print(json.dumps({"total": None, "unique_ips": None, "last_accessed": None}))
                else:
                    print("stats unavailable (log_path not configured, run toss init to set it up)")
                return
            if not args.json:
                print("fetching stats...", file=sys.stderr)
            data = get_stats(config, args.slug)
            if args.json:
                print(json.dumps(data))
            else:
                last = data["last_accessed"] if data["last_accessed"] is not None else "never"
                print(f"stats for {args.slug}")
                print(f"  total requests   {data['total']}")
                print(f"  unique visitors  {data['unique_ips']}")
                print(f"  last accessed    {last}")

    except (FileNotFoundError, RuntimeError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
