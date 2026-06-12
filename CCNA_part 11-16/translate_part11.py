#!/usr/bin/env python3
"""
CCNA Part 11 ODT Translator — Analyze and count paragraphs
"""
import zipfile
import re
from xml.etree import ElementTree as ET

INPUT_FILE = "Part 11.odt"

# Read ODT
with zipfile.ZipFile(INPUT_FILE, "r") as z:
    xml_content = z.read("content.xml").decode("utf-8")

NS_TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
NS_TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
NS_DRAW = "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"

root = ET.fromstring(xml_content)
paragraphs = list(root.iter(f"{{{NS_TEXT}}}p"))


def get_text_odt(para):
    """Extract all text from an ODT paragraph."""
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


# Skip patterns
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
    re.compile(r"^\s*[{}\[\]\",:]+\s*$"),
    re.compile(r"^(Option\s+[A-D]|R\d+|SW\d+|PC\d+)$", re.I),
]

MIN_LENGTH = 4

def should_translate(text):
    t = text.strip()
    if not t or len(t) < MIN_LENGTH:
        return False
    for pat in SKIP_PATTERNS:
        if pat.search(t):
            return False
    return bool(re.search(r"\b[A-Za-z]{4,}\b", t))


# Count stats
total = 0
translatable = 0
for p in paragraphs:
    txt = get_text_odt(p)
    if txt:
        total += 1
        if should_translate(txt):
            translatable += 1

print(f"Total paragraphs with text: {total}")
print(f"Paragraphs to translate: {translatable}")
print(f"Paragraphs to skip: {total - translatable}")

# Tables
tables = list(root.iter(f"{{{NS_TABLE}}}table"))
print(f"Tables found: {len(tables)}")

table_paras = 0
for t in tables:
    table_paras += len(list(t.iter(f"{{{NS_TEXT}}}p")))
print(f"Paragraphs inside tables: {table_paras}")

# Images
frames = list(root.iter(f"{{{NS_DRAW}}}frame"))
print(f"Draw frames (images): {len(frames)}")

# Show sample of translatable paragraphs
print("\n--- SAMPLE TRANSLATABLE PARAGRAPHS ---")
count = 0
for p in paragraphs:
    txt = get_text_odt(p)
    if txt and should_translate(txt):
        print(f"  [{count}] {txt[:150]}")
        count += 1
        if count >= 20:
            break

print("\n--- SAMPLE SKIPPED PARAGRAPHS ---")
count = 0
for p in paragraphs:
    txt = get_text_odt(p)
    if txt and not should_translate(txt):
        print(f"  [SKIP] {txt[:150]}")
        count += 1
        if count >= 15:
            break
