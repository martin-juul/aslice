"""Map resource locations in markup without rewriting documentation examples."""

from html import escape, unescape
from html.parser import HTMLParser
import re


def rewrite_css(text, resolve):
    def resource(match):
        delimiter, value = match.groups()
        return "url(" + delimiter + resolve(value.strip()) + delimiter + ")"

    text = re.sub(r"url\(\s*([\"']?)([^)\"']+)\1\s*\)", resource, text)
    return re.sub(
        r"(@import\s+)([\"'])(.*?)\2",
        lambda match: match[1] + match[2] + resolve(match[3]) + match[2],
        text,
    )


class HtmlRoutes(HTMLParser):
    def __init__(self, text, resolve):
        super().__init__(convert_charrefs=False)
        self.text = text
        self.resolve = resolve
        self.line_offsets = [0] + [match.end() for match in re.finditer("\n", text)]
        self.edits = []
        self.in_style = False

    def replace(self, original, replacement):
        if original != replacement:
            line, column = self.getpos()
            start = self.line_offsets[line - 1] + column
            self.edits.append((start, start + len(original), replacement))

    def attribute(self, match):
        name, spacing, delimiter, value = match.groups()
        if name.lower() not in {
            "href",
            "xlink:href",
            "src",
            "srcset",
            "poster",
            "action",
            "style",
        }:
            return match[0]
        value = unescape(value)
        if name.lower() == "style":
            value = rewrite_css(value, self.resolve)
        elif name.lower() == "srcset":
            choices = []
            for choice in value.split(","):
                parts = choice.strip().split()
                if parts:
                    parts[0] = self.resolve(parts[0])
                    choices.append(" ".join(parts))
            value = ", ".join(choices)
        else:
            value = self.resolve(value)
        return f"{name}{spacing}{delimiter}{escape(value, quote=True)}{delimiter}"

    def handle_starttag(self, tag, _attributes):
        original = self.get_starttag_text()
        replacement = re.sub(
            r"([\w:-]+)(\s*=\s*)([\"'])(.*?)\3",
            self.attribute,
            original,
            flags=re.I | re.S,
        )
        self.replace(original, replacement)
        self.in_style = tag == "style"

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            self.replace(data, rewrite_css(data, self.resolve))

    def rewritten(self):
        self.feed(self.text)
        self.close()
        text = self.text
        for start, end, replacement in reversed(self.edits):
            text = text[:start] + replacement + text[end:]
        return text
