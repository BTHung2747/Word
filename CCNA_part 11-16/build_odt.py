#!/usr/bin/env python3
"""
CCNA Part 11 ODT Translator
Reads Part 11.odt, replaces English text with Vietnamese translations,
preserves all images, tables, formatting, and outputs Part 11-Vi.odt
"""
import zipfile
import re
import json
import os
import shutil
import tempfile
from xml.etree import ElementTree as ET

INPUT_FILE = "Part 11.odt"
OUTPUT_FILE = "Part 11-Vi.odt"
TRANSLATIONS_FILE = "part11_translations.json"

NS_TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
NS_DRAW = "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"

# Register all namespaces to preserve them in output
NAMESPACES = {
    'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
    'style': 'urn:oasis:names:tc:opendocument:xmlns:style:1.0',
    'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
    'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    'draw': 'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0',
    'fo': 'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0',
    'xlink': 'http://www.w3.org/1999/xlink',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'meta': 'urn:oasis:names:tc:opendocument:xmlns:meta:1.0',
    'number': 'urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0',
    'svg': 'urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0',
    'chart': 'urn:oasis:names:tc:opendocument:xmlns:chart:1.0',
    'dr3d': 'urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0',
    'math': 'http://www.w3.org/1998/Math/MathML',
    'form': 'urn:oasis:names:tc:opendocument:xmlns:form:1.0',
    'script': 'urn:oasis:names:tc:opendocument:xmlns:script:1.0',
    'ooo': 'http://openoffice.org/2004/office',
    'ooow': 'http://openoffice.org/2004/writer',
    'oooc': 'http://openoffice.org/2004/calc',
    'dom': 'http://www.w3.org/2001/xml-events',
    'xforms': 'http://www.w3.org/2002/xforms',
    'xsd': 'http://www.w3.org/2001/XMLSchema',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'rpt': 'http://openoffice.org/2005/report',
    'of': 'urn:oasis:names:tc:opendocument:xmlns:of:1.2',
    'xhtml': 'http://www.w3.org/1999/xhtml',
    'grddl': 'http://www.w3.org/2003/g/data-view#',
    'officeooo': 'http://openoffice.org/2009/office',
    'tableooo': 'http://openoffice.org/2009/table',
    'drawooo': 'http://openoffice.org/2010/draw',
    'calcext': 'urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0',
    'loext': 'urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0',
    'field': 'urn:openoffice:names:experimental:ooo-ms-interop:xmlns:field:1.0',
    'css3t': 'http://www.w3.org/TR/css3-text/',
    'formx': 'urn:openoffice:names:experimental:ooxml-odf-interop:xmlns:form:1.0',
}

for prefix, uri in NAMESPACES.items():
    ET.register_namespace(prefix, uri)


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


def set_text_odt(para, new_text):
    """Set new text on an ODT paragraph, preserving draw:frame (images)."""
    # Preserve draw:frame children (images)
    frames_to_keep = []
    for child in list(para):
        ns = child.tag.split("}")[0].lstrip("{") if "}" in child.tag else ""
        if ns == NS_DRAW:
            frames_to_keep.append(child)
        else:
            para.remove(child)
    
    # Set new text
    para.text = new_text
    
    # Re-add preserved frames
    for frame in frames_to_keep:
        para.append(frame)


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


def main():
    # Load translations
    if not os.path.exists(TRANSLATIONS_FILE):
        print(f"ERROR: {TRANSLATIONS_FILE} not found!")
        return
    
    with open(TRANSLATIONS_FILE, "r", encoding="utf-8") as f:
        translations = json.load(f)
    
    # Create index -> translation mapping
    trans_map = {item["index"]: item["translated"] for item in translations}
    print(f"Loaded {len(trans_map)} translations")
    
    # Read ODT
    with zipfile.ZipFile(INPUT_FILE, "r") as z:
        xml_content = z.read("content.xml").decode("utf-8")
    
    # Parse XML
    root = ET.fromstring(xml_content)
    paragraphs = list(root.iter(f"{{{NS_TEXT}}}p"))
    print(f"Total paragraphs: {len(paragraphs)}")
    
    # Apply translations
    replaced = 0
    skipped = 0
    for i, para in enumerate(paragraphs):
        if i in trans_map and trans_map[i]:
            set_text_odt(para, trans_map[i])
            replaced += 1
        else:
            txt = get_text_odt(para)
            if txt and should_translate(txt):
                skipped += 1
    
    print(f"Replaced: {replaced}, Skipped (no translation): {skipped}")
    
    # Write modified XML
    xml_output = ET.tostring(root, encoding="unicode", xml_declaration=False)
    xml_output = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_output
    
    # Repack ODT
    tmpdir = tempfile.mkdtemp()
    try:
        # Extract original
        with zipfile.ZipFile(INPUT_FILE, "r") as z:
            z.extractall(tmpdir)
        
        # Overwrite content.xml
        with open(os.path.join(tmpdir, "content.xml"), "w", encoding="utf-8") as f:
            f.write(xml_output)
        
        # Repack - mimetype must be first and uncompressed
        with zipfile.ZipFile(OUTPUT_FILE, "w", zipfile.ZIP_DEFLATED) as zout:
            # mimetype first, uncompressed
            mimetype_path = os.path.join(tmpdir, "mimetype")
            if os.path.exists(mimetype_path):
                zout.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
            
            for dirpath, dirs, files in os.walk(tmpdir):
                for fname in files:
                    fpath = os.path.join(dirpath, fname)
                    arcname = os.path.relpath(fpath, tmpdir)
                    if arcname == "mimetype":
                        continue  # already added
                    zout.write(fpath, arcname)
        
        print(f"\nOutput saved to: {OUTPUT_FILE}")
    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    main()
