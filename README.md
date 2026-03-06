<div align="center">
  <img src="assets/logo-circle.svg" alt="toss logo" width="96" />
</div>

# Toss
Toss is a minimal CLI to deploy and share static sites, HTML, and Markdown from your own server. Fast configuration and easy to setup so you can use it from about everywhere and share your work with private URLs.

## Features
- Deploy a Markdown file, an HTML file, or a full directory with a single command
- Markdown pages render in the browser with LaTeX (KaTeX), syntax highlighting, footnotes, callouts, and Mermaid diagrams
- Random slugs by default, custom slugs with `--slug`
- Build-and-deploy in one step with `--build`
- List, hide, unhide, and permanently delete deployments
- Visit stats (total requests, unique visitors, last accessed) via Caddy JSON logs
- Machine-readable JSON output with `--json` (deploy, list, stats)
- Skip confirmation prompts with `-y` for scripting and automation
- Zero server-side dependencies beyond Caddy and SSH access

## Installation and setup
> [!NOTE]
> The following prerequisites are needed before installing toss.
> - [Python](https://www.python.org/) 3.10+
> - [uv](https://docs.astral.sh/uv/)
> - [git](https://git-scm.com/)
> - `rsync` and `ssh` available in PATH (client-side)
> - SSH access to a server running [Caddy](https://caddyserver.com/)

### Server-side setup
You'll first need to configure your server to serve files through SSH and [Caddy](https://caddyserver.com/).
This section assumes you are running the commands on your server.

Add a DNS A record: `share` (or anything you like) pointing to your server IP.

Create the sites directory and give your SSH user write access:
```sh
sudo mkdir -p /srv/sites
sudo chown youruser:youruser /srv/sites
```

Add a block to your Caddyfile for the share subdomain:
```
share.yourdomain.com {
    root * /srv/sites
    file_server
    header X-Robots-Tag "noindex, nofollow"
    handle_errors {
        rewrite * /404.html
        file_server
    }
}
```

If running Caddy in Docker, also mount `/srv/sites` in your Caddy container's volumes:
```yaml
volumes:
  - /srv/sites:/srv/sites:ro
```

Copy the 404 page to your server. Feel free to edit `assets/404.html` to add your own contact info, and edit `toss_cli/templates/markdown_page.html` to customize the Markdown rendering theme before installing:
```sh
scp assets/404.html user@your-server:/srv/sites/404.html
```

Then restart Caddy:
```sh
# assuming systemd
sudo systemctl reload caddy
# or if using Docker
docker compose up -d caddy
```

### Enabling visit stats
`toss stats` parses Caddy's JSON access logs over SSH. Note that this required Caddy logging and thus is optional.

Add a `log` block to your Caddy site block:
```
share.yourdomain.com {
    log {
        output file /var/log/caddy/access.log
        format json
    }
    root * /srv/sites
    ...
}
```

If running Caddy in Docker, mount the log directory in your docker-compose.yml:
```yaml
volumes:
  - /var/log/caddy:/var/log/caddy
```

Create the log directory and make it readable by your SSH user (run on server):
```sh
sudo mkdir -p /var/log/caddy
sudo chmod o+rx /var/log/caddy
# after the first restart, also:
sudo chmod o+r /var/log/caddy/access.log
```

Restart Caddy, then re-run `toss init` and enter the log path (default: `/var/log/caddy/access.log`).

### Local CLI
Once the server is configured, install toss:
```sh
uv tool install toss-cli
```

Once toss is installed, run the interactive setup wizard once:
```sh
toss init
```
This will prompt you for your server details, validate SSH connectivity, and save a config file at `~/.config/toss/config.toml`.

> [!NOTE]
> Re-run `toss init` at any time to update your configuration. If you prefer to edit it manually, it uses the following format:
> ```toml
> host = "user@my-server"
> domain = "share.mydomain.com"
> remote_path = "/srv/sites"
> slug_length = 6
> log_path = "/var/log/caddy/access.log"  # optional, needed for toss stats
> ```

## Usage

```sh
# deploy a Markdown file, an HTML file, or a directory
toss deploy path/to/file.md
toss deploy path/to/page.html
toss deploy path/to/site/

# custom slug and title (for Markdown files)
toss deploy report.md --slug my-report
toss deploy report.md --title "My Report"

# build then deploy
toss deploy . --build "npm run build"
toss deploy . --build "npm run build" --out dist

# skip confirmation prompts (useful for scripts)
toss deploy path/to/site/ --slug my-site -y
toss undeploy <slug> -y

# list all deployments
toss list

# hide (makes URL return 404) and unhide
toss hide <slug>
toss unhide <slug>

# permanently delete
toss undeploy <slug>

# show visit stats
toss stats <slug>

# machine-readable JSON output
toss --json deploy path/to/site/
toss --json list
toss --json stats <slug>
```
