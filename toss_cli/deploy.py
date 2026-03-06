import random
import shutil
import string
import subprocess
import tempfile
from pathlib import Path

from toss_cli import remote, templates
from toss_cli.ssh import validate_slug

_BUILD_OUT_DIRS = ("dist", "build", "out", "public")


def _random_slug(length: int) -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=length))


def _find_free_slug(config: dict) -> str:
    for _ in range(5):
        slug = _random_slug(config["slug_length"])
        if not remote.check_slug_exists(config, slug):
            return slug
    raise RuntimeError("Could not find a free slug after 5 attempts, try again")


def _detect_input(path: Path) -> str:
    if path.is_dir():
        return "directory"
    if path.suffix == ".md":
        return "md"
    if path.suffix in (".html", ".htm"):
        return "html"
    raise ValueError(f"Unsupported file type: {path.suffix} (expected .md, .html, or a directory)")


def _prepare_build(cmd: str, out_dir: str | None) -> Path:
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        raise RuntimeError(f"Build command failed with exit code {result.returncode}")
    if out_dir:
        p = Path(out_dir)
        if not p.is_dir():
            raise RuntimeError(f"--out directory not found: {out_dir}")
        return p
    for name in _BUILD_OUT_DIRS:
        p = Path(name)
        if p.is_dir():
            return p
    raise RuntimeError("Build succeeded but no output directory found, use --out")


def deploy(
    path: str,
    slug: str | None = None,
    build_cmd: str | None = None,
    out_dir: str | None = None,
    yes: bool = False,
) -> str:
    from toss_cli.config import load_config

    config = load_config()

    # build mode
    if build_cmd:
        local_dir = _prepare_build(build_cmd, out_dir)
        input_type = "directory"
    else:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        input_type = _detect_input(p)
        local_dir = None

    # resolve slug
    if slug:
        validate_slug(slug)
        if remote.check_slug_exists(config, slug):
            if not yes:
                answer = input(f"'{slug}' is already taken, overwrite? [y/N] ").strip().lower()
                if answer != "y":
                    raise RuntimeError("Deploy cancelled")
    else:
        slug = _find_free_slug(config)

    # prepare local staging dir
    tmp = None
    try:
        if input_type == "md":
            md_text = Path(path).read_text(encoding="utf-8")
            title = Path(path).stem.replace("-", " ").replace("_", " ").title()
            html = templates.render_page(title, md_text)
            tmp = tempfile.mkdtemp()
            Path(tmp, "index.html").write_text(html, encoding="utf-8")
            local_dir = tmp
        elif input_type == "html":
            tmp = tempfile.mkdtemp()
            shutil.copy(Path(path), Path(tmp, "index.html"))
            local_dir = tmp
        else:
            local_dir = str(local_dir or path)

        remote.rsync_deploy(config, str(local_dir), slug)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    return f"https://{config['domain']}/{slug}/"
