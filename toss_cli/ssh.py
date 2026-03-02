import re
import subprocess

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")


def validate_slug(slug: str) -> None:
    if not _SLUG_RE.match(slug):
        raise ValueError(f"Invalid slug '{slug}': use lowercase letters, digits, and hyphens only")


def run_ssh(host: str, cmd: str, opts: list[str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["ssh", *(opts or []), host, cmd],
        capture_output=True,
        text=True,
    )
