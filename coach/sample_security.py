"""Permit only the exact inline assets in our two pinned, public MDN samples."""
import base64
import hashlib
from functools import lru_cache
from html.parser import HTMLParser
from .settings import ROOT

BASE_CSP = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"


class InlineAssets(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.tag = None
        self.parts = []
        self.hashes = {'script': [], 'style': []}

    def handle_starttag(self, tag, attrs):
        if tag in self.hashes and not dict(attrs).get('src'):
            self.tag, self.parts = tag, []

    def handle_data(self, data):
        if self.tag: self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == self.tag:
            raw = ''.join(self.parts).replace('\r\n', '\n').replace('\r', '\n')
            value = base64.b64encode(hashlib.sha256(raw.encode()).digest()).decode()
            self.hashes[tag].append("'sha256-"+value+"'")
            self.tag = None


@lru_cache(maxsize=8)
def sample_csp(path):
    name = next((name for name in ('shopping', 'dialog')
                 if path in (f'/samples/public/{name}/', f'/samples/public/{name}/index.html')), None)
    if name is None: return BASE_CSP
    parser = InlineAssets()
    parser.feed((ROOT/'examples/public'/name/'index.html').read_text(encoding='utf-8'))
    result = BASE_CSP
    for tag, hashes in parser.hashes.items():
        if hashes: result = result.replace(f"{tag}-src 'self'", f"{tag}-src 'self' "+' '.join(hashes))
    return result
