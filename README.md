<div align="center">
  <img src="assets/logo-circle.svg" alt="toss logo" width="96" />
</div>

# Toss
Toss is a minimal CLI to deploy and share static sites, HTML, and Markdown from your own server. Fast configuration and easy to setup so you can use it from about everywhere and share your work with private URLs.


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

Copy the 404 page to your server — feel free to edit it to add your own contact info:
```sh
scp assets/404.html user@your-server:/srv/sites/404.html
```

Then restart Caddy:
```sh
# assuming systemd
sudo systemctl reload caddy
docker compose up -d caddy
```

### Local CLI
Once the server is configured, clone the repo and install toss locally:
```sh
git clone https://github.com/brayevalerien/toss
cd toss
uv tool install .
```

Once toss is installed, run the interactive setup wizard once:
```sh
toss init
```
This will prompt you for your server details, validate SSH connectivity, and save a config file at `~/.config/toss/config.toml`.
> Re-run `toss init` at any time to update your configuration. If you prefer to edit it manually, it uses the following format:
> ```toml
> host = "user@my-server"
> domain = "share.mydomain.com"
> remote_path = "/srv/sites"
> slug_length = 6 # length of auto-generated slugs
> ```
