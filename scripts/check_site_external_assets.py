from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ASSET_ATTRIBUTES = {
    "audio": ("src",),
    "img": ("src", "srcset"),
    "script": ("src",),
    "source": ("src", "srcset"),
    "video": ("poster", "src"),
}


class AssetParser(HTMLParser):
    def __init__(self, source: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.external: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = dict(attrs)

        if tag == "link":
            rel = set((values.get("rel") or "").lower().split())
            if rel & {"stylesheet", "icon", "preload", "modulepreload"}:
                self._check(values.get("href"))
            return

        for attribute in ASSET_ATTRIBUTES.get(tag, ()):
            self._check(values.get(attribute))

    def _check(self, value: str | None) -> None:
        if not value:
            return

        for candidate in value.split(","):
            url = candidate.strip().split(" ", 1)[0]
            parsed = urlparse(url)

            if parsed.scheme in {"http", "https"}:
                self.external.append(url)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_site_external_assets.py <site-dir>")

    site = Path(sys.argv[1])

    if not site.is_dir():
        raise SystemExit(f"site directory not found: {site}")

    failures: list[tuple[Path, str]] = []

    for path in sorted(site.rglob("*.html")):
        parser = AssetParser(path)
        parser.feed(path.read_text(encoding="utf-8"))

        failures.extend((path, url) for url in parser.external)

    if failures:
        print("External runtime assets remain after the privacy build:", file=sys.stderr)
        for path, url in failures:
            print(f"  {path}: {url}", file=sys.stderr)
        return 1

    print("External runtime asset audit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
