#!/usr/bin/env python3
"""Check generated HTML without making network requests."""

from html.parser import HTMLParser
from pathlib import Path
import sys
from urllib.parse import unquote, urljoin, urlsplit


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.language = None
        self.headings = []
        self.heading = None
        self.resources = []
        self.images = []
        self.has_favicon = False
        self.ids = set()
        self.fragments = []

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        if tag == "a" and attributes.get("href", "").startswith("#") and attributes["href"] != "#":
            self.fragments.append(unquote(attributes["href"][1:]))
        if tag == "html":
            self.language = attributes.get("lang")
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.heading = [tag, ""]
            self.headings.append(self.heading)
        if tag in ("a", "link") and attributes.get("href"):
            self.resources.append(attributes["href"])
        if tag in ("img", "script") and attributes.get("src"):
            self.resources.append(attributes["src"])
        if tag == "link" and attributes.get("rel") == "icon":
            self.has_favicon = True
            if not urlsplit(attributes.get("href", "")).path.lower().endswith((".jpg", ".jpeg", ".png", ".ico", ".svg")):
                raise ValueError("favicon must reference an image")
        if tag == "img":
            self.images.append(attributes)
            for candidate in attributes.get("srcset", "").split(","):
                if candidate.strip():
                    self.resources.append(candidate.strip().split()[0])

    def handle_data(self, data):
        if self.heading is not None:
            self.heading[1] += data

    def handle_endtag(self, tag):
        if self.heading is not None and tag == self.heading[0]:
            self.heading = None


def check_site(directory):
    directory = Path(directory).resolve()
    files = sorted(directory.rglob("*.html"))
    if not files:
        raise ValueError("no generated HTML found")
    errors = []
    for filename in files:
        relative = filename.relative_to(directory)
        page = Page()
        try:
            page.feed(filename.read_text())
        except ValueError as error:
            errors.append(f"{relative}: {error}")
        if page.language != "zh-Hant":
            errors.append(f"{relative}: expected lang=zh-Hant")
        if len([h for h in page.headings if h[0] == "h1"]) != 1:
            errors.append(f"{relative}: expected exactly one h1")
        if any(not text.strip() for _, text in page.headings):
            errors.append(f"{relative}: empty heading")
        if not page.has_favicon:
            errors.append(f"{relative}: missing favicon")
        for image in page.images:
            if "alt" not in image or not image.get("width") or not image.get("height"):
                errors.append(f"{relative}: image needs alt, width, and height")
        for fragment in page.fragments:
            if fragment not in page.ids:
                errors.append(f"{relative}: missing fragment target #{fragment}")
        for reference in page.resources:
            url = urlsplit(urljoin(f"https://www.ntuadf.org/{relative.as_posix()}", reference))
            if url.scheme not in ("http", "https") or url.netloc != "www.ntuadf.org":
                continue
            path = directory / unquote(url.path).lstrip("/")
            if not path.exists():
                errors.append(f"{relative}: missing local resource {reference}")
    if errors:
        raise ValueError("\n".join(errors))
    print(f"Checked {len(files)} HTML pages: headings, language, images, favicons, and local resources OK.")


if __name__ == "__main__":
    try:
        check_site(sys.argv[1] if len(sys.argv) > 1 else "public")
    except ValueError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
