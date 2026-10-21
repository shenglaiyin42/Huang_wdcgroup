"""Embed WDC's English translations alongside the Chinese Quarto source.

Uses only Python's standard library so local previews and GitHub Pages use the
same build without extra dependencies. All four pages are validated before any
HTML is written. Re-running the hook preserves the original Chinese copy.
"""

import hashlib
import json
import os
import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path


SITE = Path(__file__).resolve().parents[1]
OUTPUT = Path(os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "_site"))
if not OUTPUT.is_absolute():
    OUTPUT = SITE / OUTPUT
TRANSLATIONS = json.loads((SITE / "assets/i18n/en.json").read_text(encoding="utf-8"))
TITLES = {"index": ("主页", "Home"), "people": ("研究团队", "Team"),
          "publications": ("研究组论文发表", "Group Publications"),
          "contact": ("联系课题组", "Contact the Group")}
VOID = set("area base br col embed hr img input link meta param source track wbr".split())
HAN = re.compile(r"[\u3400-\u9fff]")


class Node:
    def __init__(self, tag, attrs=None, children=None, text=""):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.children = children or []
        self.text = text

    def has_class(self, name):
        return name in (self.attrs.get("class") or "").split()

    def find(self, predicate):
        if predicate(self):
            return self
        for child in self.children:
            found = child.find(predicate)
            if found:
                return found
        return None

    def html(self, raw=False):
        if self.tag == "#raw":
            return self.text
        if self.tag == "#text":
            return self.text if raw else escape(self.text, quote=False)
        content = "".join(child.html(self.tag in {"script", "style"}) for child in self.children)
        if self.tag == "#document":
            return content
        attrs = "".join(" " + key if value is None else f' {key}="{escape(value, quote=True)}"'
                        for key, value in self.attrs.items())
        start = f"<{self.tag}{attrs}>"
        return start if self.tag in VOID else start + content + f"</{self.tag}>"


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self.stack = [self.root]
        self.feed(source)
        self.close()

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(Node("#text", text=data))

    def handle_decl(self, decl):
        self.stack[-1].children.append(Node("#raw", text="<!" + decl + ">"))

    def handle_comment(self, data):
        self.stack[-1].children.append(Node("#raw", text="<!--" + data + "-->"))


def text(value):
    return Node("#text", text=value)


def pair(chinese, english):
    return [Node("span", {"data-wdc-copy": language, "lang": lang}, [text(value)])
            for language, lang, value in (("zh", "zh-CN", chinese), ("en", "en", english))]


def restore(node):
    """Unwrap only our own Chinese spans before processing a preview rebuild."""
    children = []
    for child in node.children:
        language = child.attrs.get("data-wdc-copy")
        if language == "en" or child.has_class("wdc-language-switch"):
            continue
        restore(child)
        children.extend(child.children if language == "zh" else [child])
    node.children = children


def translate(node):
    if node.tag in {"script", "style", "title", "#raw"}:
        return
    for attribute in ("alt", "title", "aria-label"):
        original = node.attrs.get("data-wdc-attr-zh-" + attribute, node.attrs.get(attribute))
        if original and HAN.search(original):
            if original not in TRANSLATIONS:
                raise ValueError(f"Missing {attribute} translation: {original}")
            node.attrs["data-wdc-attr-zh-" + attribute] = original
            node.attrs["data-wdc-attr-en-" + attribute] = TRANSLATIONS[original]
            node.attrs[attribute] = original
    children = []
    for child in node.children:
        if child.tag == "#text":
            key = child.text.strip()
            if key in TRANSLATIONS:
                leading = child.text[:len(child.text) - len(child.text.lstrip())]
                trailing = child.text[len(child.text.rstrip()):]
                children.extend([text(leading), *pair(key, TRANSLATIONS[key]), text(trailing)])
                continue
            if HAN.search(key):
                raise ValueError(f"Missing text translation: {key}")
        translate(child)
        children.append(child)
    node.children = children


def build(path):
    root = Document(path.read_text(encoding="utf-8")).root
    restore(root)
    translate(root)
    html = root.find(lambda node: node.tag == "html")
    chinese, english = TITLES[path.stem]
    html.attrs.update({"lang": "zh-CN", "xml:lang": "zh-CN",
                       "data-wdc-title-zh": chinese + " | 野生动物疫病与保护研究组",
                       "data-wdc-title-en": english + " | Wildlife Disease & Conservation Group"})
    root.find(lambda node: node.tag == "title").children = [text(html.attrs["data-wdc-title-zh"])]
    brand = root.find(lambda node: node.has_class("navbar-brand"))
    brand.children = [
        Node("span", {"class": "brand-chinese"}, pair("野生动物疫病与保护研究组", "Wildlife Disease & Conservation Group")),
        Node("span", {"class": "brand-english"}, pair("Wildlife Disease & Conservation Group", "WDC Group")),
    ]
    switch = Node("div", {"class": "wdc-language-switch", "role": "group",
                          "aria-label": "语言选择", "data-wdc-attr-zh-aria-label": "语言选择",
                          "data-wdc-attr-en-aria-label": "Language"})
    for language, label in (("zh", "中文"), ("en", "EN")):
        switch.children.append(Node("button", {"type": "button", "data-wdc-language": language,
                                               "lang": "zh-CN" if language == "zh" else "en",
                                               "aria-label": "显示中文" if language == "zh" else "View in English",
                                               "aria-pressed": "true" if language == "zh" else "false",
                                               "disabled": None}, [text(label)]))
    root.find(lambda node: node.has_class("navbar-brand-container")).children.append(switch)
    # Cache-bust changed assets without changing external or academic links.
    def version(node):
        attribute = "href" if node.tag == "link" else "src" if node.tag == "script" else None
        if attribute and node.attrs.get(attribute):
            href = node.attrs[attribute].split("?", 1)[0]
            if href in {"language.css", "assets/js/language-switch.js"}:
                digest = hashlib.sha256((SITE / href).read_bytes()).hexdigest()[:12]
                node.attrs[attribute] = href + "?v=" + digest
        for child in node.children:
            version(child)
    version(root)
    return root.html()


def main():
    rendered = {}
    for name in TITLES:
        path = OUTPUT / (name + ".html")
        if path.exists():
            rendered[path] = build(path)
    if not rendered:
        raise FileNotFoundError("No rendered WDC pages were found")
    for path, html in rendered.items():
        path.write_text(html, encoding="utf-8")
    print(f"Embedded Chinese and English copy in {len(rendered)} pages.")


if __name__ == "__main__":
    main()
