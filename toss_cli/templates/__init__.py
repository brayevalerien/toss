import html
import json
from importlib.resources import files


def render_page(title: str, content: str) -> str:
    template = files(__name__).joinpath("markdown_page.html").read_text(encoding="utf-8")
    return (
        template
        .replace("TOSS_TITLE", html.escape(title))
        .replace("TOSS_CONTENT", json.dumps(content))
    )
