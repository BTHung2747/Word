#!/usr/bin/env python3
"""Extract all translatable text from Part 11.odt with paragraph indices."""
import zipfile
import re
import json
from xml.etree import ElementTree as ET

INPUT_FILE = "Part 11.odt"

with zipfile.ZipFile(INPUT_FILE, "r") as z:
    xml_content = z.read("content.xml").decode("utf-8")

NS_TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
root = ET.fromstring(xml_content)
paragraphs = list(root.iter(f"{{{NS_TEXT}}}p"))


def get_text_odt(para):
    parts = []
    if para.text:
        parts.append(para.text)
    for child in para:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "line-break":
            parts.append("\n")
        if child.text:
            parts.append(child.text)
        for sub in child:
            sub_tag = sub.tag.split("}")[-1] if "}" in sub.tag else sub.tag
            if sub_tag == "line-break":
                parts.append("\n")
            if sub.text:
                parts.append(sub.text)
            if sub.tail:
                parts.append(sub.tail)
        if child.tail:
            parts.append(child.tail)
    return "".join(parts).strip()


SKIP_PATTERNS = [
    re.compile(r"^\s*$"),
    re.compile(r"^\s*[A-E]\.\s*$"),
    re.compile(r"^(Answer|Explanation|Reference|Note)[:\s]*$", re.I),
    re.compile(r"^https?://", re.I),
    re.compile(
        r"^\s*(interface|ip |no |show |router |switchport|"
        r"channel-group|spanning-tree|lldp|cdp|vlan\s)", re.I
    ),
    re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
    re.compile(r"^[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}"),
    re.compile(r'^\s*[{}\[\]\",:]+\s*$'),
    re.compile(r"^(Option\s+[A-D]|R\d+|SW\d+|PC\d+)$", re.I),
]


def should_translate(text):
    t = text.strip()
    if not t or len(t) < 4:
        return False
    for pat in SKIP_PATTERNS:
        if pat.search(t):
            return False
    return bool(re.search(r"\b[A-Za-z]{4,}\b", t))


# Extract all texts with their paragraph index
texts_to_translate = []
for i, p in enumerate(paragraphs):
    txt = get_text_odt(p)
    if txt and should_translate(txt):
        texts_to_translate.append({"index": i, "text": txt})

# Save to JSON
with open("part11_texts.json", "w", encoding="utf-8") as f:
    json.dump(texts_to_translate, f, ensure_ascii=False, indent=2)

print(f"Extracted {len(texts_to_translate)} paragraphs to part11_texts.json")

# Also print them in batches for review
for batch_start in range(0, len(texts_to_translate), 15):
    batch_end = min(batch_start + 15, len(texts_to_translate))
    print(f"\n=== BATCH {batch_start // 15 + 1} (paragraphs {batch_start}-{batch_end-1}) ===")
    for item in texts_to_translate[batch_start:batch_end]:
        preview = item["text"][:100].replace("\n", "\\n")
        print(f"  [{item['index']}] {preview}")
