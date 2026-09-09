"""Pin mobile table labeling while preserving native data/form elements."""
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
import re

from tests.admin.responsive_fixtures import render_fixtures


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = 0
        self.labels = 0
        self.tables = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table":
            assert attrs.get("role") == "table"
            self.tables += 1
        if tag == "th":
            assert attrs.get("scope") == "col"
            assert attrs.get("role") == "columnheader"
        if tag == "td":
            assert attrs.get("role") == "cell"
            if "colspan" not in attrs:
                self.cells += 1
        if tag == "span" and attrs.get("class") == "cell-label":
            assert attrs.get("aria-hidden") == "true"
            self.labels += 1


def test_mobile_tables_keep_column_semantics_and_localized_labels():
    with TemporaryDirectory() as directory:
        output = Path(directory)
        render_fixtures(output)
        for locale in ("vi", "en"):
            for name in ("dashboard", "users", "user_detail", "stations", "station_detail"):
                parser = TableParser()
                parser.feed((output / f"{locale}-{name}.html").read_text(encoding="utf-8"))
                assert parser.tables > 0, name
                assert parser.cells == parser.labels > 0, name


def test_preview_navigation_resolves_to_existing_local_pages():
    with TemporaryDirectory() as directory:
        output = Path(directory)
        render_fixtures(output)
        for page in output.glob('*.html'):
            html = page.read_text(encoding='utf-8')
            links = re.findall(r'<a\b[^>]*?href="([^"]*)"', html)
            assert links
            for link in links:
                assert link.endswith('.html'), (page.name, link)
                assert (output / link.lstrip('/')).is_file(), (page.name, link)
            locale, name = page.stem.split('-', 1)
            if name != 'error':
                other = 'en' if locale == 'vi' else 'vi'
                assert f'href="/{other}-{name}.html"' in html
