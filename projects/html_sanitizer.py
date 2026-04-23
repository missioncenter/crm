from html import escape
from html.parser import HTMLParser
import re
from urllib.parse import urlparse


ALLOWED_TAGS = {"p", "br", "strong", "b", "em", "i", "u", "ul", "ol", "li", "div", "a"}
ALLOWED_ATTRS = {
    "a": {"href", "title", "target", "rel"},
}
TEXT_ALIGN_RE = re.compile(r"^\s*text-align\s*:\s*(left|center|right|justify)\s*;?\s*$", re.IGNORECASE)


def _is_safe_href(value):
    parsed = urlparse(value)
    if not parsed.scheme:
        return True
    return parsed.scheme in {"http", "https", "mailto"}


class RichTextSanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            return
        if tag == "br":
            self.parts.append("<br>")
            return

        attr_pairs = []
        allowed_attrs = ALLOWED_ATTRS.get(tag, set())
        for name, value in attrs:
            if value is None:
                continue
            if tag == "a" and name in allowed_attrs:
                if name == "href" and not _is_safe_href(value):
                    continue
                if name == "target" and value not in {"_blank", "_self", "_parent", "_top"}:
                    continue
                attr_pairs.append(f'{name}="{escape(value, quote=True)}"')
                continue
            if tag in {"p", "div", "li"} and name == "align" and value.lower() in {"left", "center", "right", "justify"}:
                attr_pairs.append(f'align="{escape(value, quote=True)}"')
                continue
            if tag in {"p", "div", "li"} and name == "style":
                match = TEXT_ALIGN_RE.match(value)
                if match:
                    attr_pairs.append(f'style="text-align: {match.group(1).lower()};"')
                continue

        attrs_text = f" {' '.join(attr_pairs)}" if attr_pairs else ""
        self.parts.append(f"<{tag}{attrs_text}>")

    def handle_endtag(self, tag):
        if tag in ALLOWED_TAGS and tag != "br":
            self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        self.parts.append(escape(data))

    def handle_entityref(self, name):
        self.parts.append(f"&{name};")

    def handle_charref(self, name):
        self.parts.append(f"&#{name};")


def sanitize_rich_text(value):
    if not value:
        return ""
    parser = RichTextSanitizer()
    parser.feed(value)
    parser.close()
    return "".join(parser.parts)