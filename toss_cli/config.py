import shutil
import time
from pathlib import Path

import tomllib

from toss_cli.ssh import run_ssh

CONFIG_PATH = Path.home() / ".config" / "toss" / "config.toml"

DEFAULTS: dict[str, object] = {
    "remote_path": "/srv/sites",
    "slug_length": 6,
}


REQUIRED_KEYS = ("host", "domain", "remote_path", "slug_length")


def load_config() -> dict[str, object]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("no config found - run `toss init` to set up")
    with open(CONFIG_PATH, "rb") as f:
        config = tomllib.load(f)
    missing = [k for k in REQUIRED_KEYS if k not in config]
    if missing:
        raise ValueError(f"config missing required keys: {', '.join(missing)}\nrun `toss init` to fix your configuration.")
    return config


def _check_tools() -> None:
    missing = [t for t in ("rsync", "ssh") if shutil.which(t) is None]
    if missing:
        raise RuntimeError(
            f"Missing the following dependencies: {', '.join(missing)}\nPlease them via your system package manager (e.g. apt install rsync openssh-client)."
        )


def _prompt(label: str, default: str | int | None = None) -> str:
    hint = f" [{default}]" if default is not None else ""
    while True:
        value = input(f"{label}{hint}: ").strip()
        if value:
            return value
        if default is not None:
            return str(default)
        print(f"  {label} is required")


def _validate_ssh(host: str) -> tuple[bool, float, str]:
    start = time.monotonic()
    result = run_ssh(host, "exit", opts=["-q", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes"])
    elapsed = time.monotonic() - start
    return result.returncode == 0, elapsed, result.stderr.strip()


def _toml_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def init_config() -> None:
    _check_tools()

    print("=== toss init - interactive configuration ===\n")

    existing: dict[str, object] = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as f:
            existing = tomllib.load(f)
        print(f"A config file was found at {CONFIG_PATH}, spam enter to keep current values\n")

    host = _prompt("SSH host (e.g. user@myserver)", existing.get("host"))
    domain = _prompt("domain (e.g. share.mydomain.com)", existing.get("domain"))
    remote_path = _prompt("remote path", existing.get("remote_path", DEFAULTS["remote_path"]))
    slug_length_raw = _prompt("slug length", existing.get("slug_length", DEFAULTS["slug_length"]))
    existing_log = existing.get("log_path", "")
    log_hint = f" [{existing_log}]" if existing_log else " [/var/log/caddy/access.log, blank to skip]"
    log_path_raw = input(f"Caddy log path{log_hint}: ").strip()
    if not log_path_raw:
        log_path_raw = existing_log or None

    try:
        slug_length = int(slug_length_raw)
        if slug_length < 2:
            print("Warning: slug length below 2 risks frequent collisions.")
    except ValueError:
        print("Warning: invalid slug length, using default (6).")
        slug_length = 6

    print(f"\nTesting SSH connection to {host}...")
    ok, elapsed, err = _validate_ssh(host)
    if ok:
        print(f"SSH connection OK! ({elapsed:.2f}s)")
    else:
        print(f"Warning: could not connect to {host}. Saving config anyway.")
        if err:
            print(f"  {err}")

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(f"host = {_toml_str(host)}\n")
        f.write(f"domain = {_toml_str(domain)}\n")
        f.write(f"remote_path = {_toml_str(remote_path)}\n")
        f.write(f"slug_length = {slug_length}\n")
        if log_path_raw:
            f.write(f"log_path = {_toml_str(log_path_raw)}\n")

    print(f"\nConfig saved to {CONFIG_PATH}")
