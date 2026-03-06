import json
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import PurePosixPath

from toss_cli.ssh import run_ssh


def _q(path) -> str:
    return shlex.quote(str(path))


def check_slug_exists(config: dict, slug: str) -> bool:
    remote = PurePosixPath(config["remote_path"]) / slug
    result = run_ssh(config["host"], f"test -d {_q(remote)}")
    return result.returncode == 0


def _check_hidden_exists(config: dict, slug: str) -> bool:
    remote = PurePosixPath(config["remote_path"]) / f".{slug}"
    result = run_ssh(config["host"], f"test -d {_q(remote)}")
    return result.returncode == 0


def get_listings(config: dict) -> list[tuple[str, bool, str]]:
    """Return [(slug, is_hidden, size)] for all deployments."""
    remote = _q(config["remote_path"])
    cmd = f"find {remote} -mindepth 1 -maxdepth 1 -type d | xargs -I{{}} du -sh {{}} 2>/dev/null"
    result = run_ssh(config["host"], cmd)
    if result.returncode != 0 and result.stderr.strip():
        raise RuntimeError(f"List failed: {result.stderr.strip()}")

    entries = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        size, path = line.split("\t", 1)
        name = PurePosixPath(path).name
        if name.startswith("."):
            entries.append((name[1:], True, size))
        else:
            entries.append((name, False, size))
    return entries


def hide_slug(config: dict, slug: str) -> None:
    if _check_hidden_exists(config, slug):
        raise ValueError(f"'{slug}' is already hidden")
    if not check_slug_exists(config, slug):
        raise ValueError(f"'{slug}' not found")
    base = PurePosixPath(config["remote_path"])
    result = run_ssh(config["host"], f"mv {_q(base / slug)} {_q(base / ('.' + slug))}")
    if result.returncode != 0:
        raise RuntimeError(f"Hide failed: {result.stderr.strip()}")


def unhide_slug(config: dict, slug: str) -> None:
    if check_slug_exists(config, slug):
        raise ValueError(f"'{slug}' is already visible")
    if not _check_hidden_exists(config, slug):
        raise ValueError(f"'{slug}' not found")
    base = PurePosixPath(config["remote_path"])
    result = run_ssh(config["host"], f"mv {_q(base / ('.' + slug))} {_q(base / slug)}")
    if result.returncode != 0:
        raise RuntimeError(f"Unhide failed: {result.stderr.strip()}")


def undeploy_slug(config: dict, slug: str) -> None:
    if not check_slug_exists(config, slug) and not _check_hidden_exists(config, slug):
        raise ValueError(f"'{slug}' not found")
    base = PurePosixPath(config["remote_path"])
    # remove whichever form exists (visible or hidden)
    target = base / (f".{slug}" if _check_hidden_exists(config, slug) else slug)
    result = run_ssh(config["host"], f"rm -rf {_q(target)}")
    if result.returncode != 0:
        raise RuntimeError(f"Undeploy failed: {result.stderr.strip()}")


def get_stats(config: dict, slug: str) -> dict:
    """Return {"total": int, "unique_ips": int, "last_accessed": str | None} for slug."""
    if not check_slug_exists(config, slug) and not _check_hidden_exists(config, slug):
        raise ValueError(f"'{slug}' not found")
    if "log_path" not in config:
        raise ValueError("log_path not set in config - run `toss init` to configure it")
    log_path = _q(config["log_path"])
    cmd = (
        f"if [ ! -f {log_path} ]; then echo TOSS_LOG_MISSING;"
        f" elif [ ! -r {log_path} ]; then echo TOSS_LOG_UNREADABLE;"
        f" else grep -F '/{slug}/' {log_path} || true; fi"
    )
    result = run_ssh(config["host"], cmd)
    if result.returncode != 0 and result.stderr.strip():
        raise RuntimeError(f"Stats failed: {result.stderr.strip()}")
    out = result.stdout.strip()
    if out == "TOSS_LOG_MISSING":
        raise RuntimeError(f"Log file not found at {config['log_path']}.\nAdd a log block to your Caddyfile and restart Caddy - see README for details.")
    if out == "TOSS_LOG_UNREADABLE":
        raise RuntimeError(f"Log file at {config['log_path']} is not readable by your SSH user.\nRun on the server: sudo chmod o+r {config['log_path']}")

    total = 0
    ips: set[str] = set()
    last_ts: float | None = None

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        status = entry.get("status", 0)
        if not (200 <= status < 400):
            continue
        total += 1
        ip = entry.get("request", {}).get("remote_ip")
        if ip:
            ips.add(ip)
        ts = entry.get("ts")
        if ts is not None and (last_ts is None or ts > last_ts):
            last_ts = ts

    if last_ts is not None:
        last_accessed = datetime.fromtimestamp(last_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    else:
        last_accessed = None

    return {"total": total, "unique_ips": len(ips), "last_accessed": last_accessed}


def get_all_stats(config: dict, slugs: list[str]) -> dict[str, dict] | None:
    """Return per-slug {"total": int, "unique_ips": int} for all slugs, or None if unavailable."""
    if "log_path" not in config:
        return None
    log_path = _q(config["log_path"])
    pattern = shlex.quote("|".join(f"/{s}/" for s in slugs))
    cmd = (
        f"if [ ! -f {log_path} ]; then echo TOSS_LOG_MISSING;"
        f" elif [ ! -r {log_path} ]; then echo TOSS_LOG_UNREADABLE;"
        f" else grep -E {pattern} {log_path} || true; fi"
    )
    result = run_ssh(config["host"], cmd)
    if result.returncode != 0 and result.stderr.strip():
        return None
    out = result.stdout.strip()
    if out in ("TOSS_LOG_MISSING", "TOSS_LOG_UNREADABLE"):
        return None

    slug_set = set(slugs)
    totals: dict[str, int] = {s: 0 for s in slugs}
    ips: dict[str, set[str]] = {s: set() for s in slugs}

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        status = entry.get("status", 0)
        if not (200 <= status < 400):
            continue
        uri = entry.get("request", {}).get("uri", "")
        parts = uri.strip("/").split("/")
        if parts and parts[0] in slug_set:
            slug = parts[0]
            totals[slug] += 1
            ip = entry.get("request", {}).get("remote_ip")
            if ip:
                ips[slug].add(ip)

    return {s: {"total": totals[s], "unique_ips": len(ips[s])} for s in slugs}


def rsync_deploy(config: dict, local_dir: str, slug: str) -> None:
    remote_dest = f"{config['host']}:{config['remote_path']}/{slug}/"
    result = subprocess.run(
        ["rsync", "-az", "--delete", "-e", "ssh", f"{local_dir}/", remote_dest],
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "Permission denied" in stderr:
            raise RuntimeError(f"Deploy failed: permission denied on remote\n  {stderr}")
        if "Connection refused" in stderr or "No route to host" in stderr:
            raise RuntimeError(f"Deploy failed: could not reach host\n  {stderr}")
        raise RuntimeError(f"Deploy failed\n  {stderr}")
