import shlex
import subprocess
from pathlib import PurePosixPath

from toss_cli.ssh import run_ssh


def _q(path) -> str:
    return shlex.quote(str(path))


def check_slug_exists(config: dict, slug: str) -> bool:
    remote = PurePosixPath(config["remote_path"]) / slug
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
    base = PurePosixPath(config["remote_path"])
    result = run_ssh(config["host"], f"mv {_q(base / slug)} {_q(base / ('.' + slug))}")
    if result.returncode != 0:
        raise RuntimeError(f"Hide failed: {result.stderr.strip()}")


def unhide_slug(config: dict, slug: str) -> None:
    base = PurePosixPath(config["remote_path"])
    result = run_ssh(config["host"], f"mv {_q(base / ('.' + slug))} {_q(base / slug)}")
    if result.returncode != 0:
        raise RuntimeError(f"Unhide failed: {result.stderr.strip()}")


def undeploy_slug(config: dict, slug: str) -> None:
    remote = PurePosixPath(config["remote_path"]) / slug
    result = run_ssh(config["host"], f"rm -rf {_q(remote)}")
    if result.returncode != 0:
        raise RuntimeError(f"Undeploy failed: {result.stderr.strip()}")


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
