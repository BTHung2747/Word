# CCNA Document Translator — Prompt for Antigravity

## NHIỆM VỤ
Dịch toàn bộ nội dung văn bản trong file tài liệu CCNA từ tiếng Anh sang tiếng Việt.

---

## BƯỚC 1 — ĐỌC FILE

### Nếu là `.docx`:
```python
import zipfile, re
from xml.etree import ElementTree as ET

with zipfile.ZipFile("input.docx", "r") as z:
    xml = z.read("word/document.xml").decode("utf-8")

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
root = ET.fromstring(xml)
paragraphs = list(root.iter(f"{{{W}}}p"))
```

### Nếu là `.odt`:
```python
import zipfile
from xml.etree import ElementTree as ET

with zipfile.ZipFile("input.odt", "r") as z:
    xml = z.read("content.xml").decode("utf-8")

NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
root = ET.fromstring(xml)
paragraphs = list(root.iter(f"{{{NS}}}p"))
```

---

## BƯỚC 2 — LẤY TEXT CỦA TỪNG PARAGRAPH

```python
def get_text(para, format="docx"):
    """Lấy toàn bộ text của một paragraph, kể cả line breaks."""
    parts = []

    if format == "docx":
        W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        for elem in para.iter(f"{{{W}}}t"):
            if elem.text:
                parts.append(elem.text)
        return "".join(parts).strip()

    elif format == "odt":
        NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
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
```

---

## BƯỚC 3 — LỌC ĐOẠN CẦN DỊCH

```python
import re

# Các pattern KHÔNG cần dịch
SKIP_PATTERNS = [
    re.compile(r"^\s*$"),                                        # dòng trống
    re.compile(r"^\s*[A-E]\.\s*$"),                              # "A." "B." đơn lẻ
    re.compile(r"^(Answer|Explanation|Reference|Note)[:\s]*$", re.I),
    re.compile(r"^https?://", re.I),                             # URL
    re.compile(r"^\s*(interface|ip |no |show |router |switchport|"
               r"channel-group|spanning-tree|lldp|cdp|vlan\s)", re.I),  # Cisco commands
    re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),         # IP address
    re.compile(r"^[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}"),             # MAC address
    re.compile(r"^\s*[{}\[\]\",:]+\s*$"),                        # JSON ký tự đặc biệt
    re.compile(r"^(Option\s+[A-D]|R\d+|SW\d+|PC\d+)$", re.I),  # Tên thiết bị đơn lẻ
]

def should_translate(text: str) -> bool:
    t = text.strip()
    if not t or len(t) < 4:
        return False
    for pat in SKIP_PATTERNS:
        if pat.search(t):
            return False
    # Phải có ít nhất 1 từ tiếng Anh thực sự
    return bool(re.search(r"\b[A-Za-z]{4,}\b", t))
```

---

## BƯỚC 4 — GỌI AI ĐỂ DỊCH (BATCH)

```python
# Gom thành batch 15 đoạn/lần để tiết kiệm token
BATCH_SIZE = 15

def build_prompt(texts: list[str]) -> str:
    numbered = "\n".join(f"[{i}] {t}" for i, t in enumerate(texts))
    return f"""Dịch các đoạn sau từ tiếng Anh sang tiếng Việt.

QUY TẮC BẮT BUỘC:
1. Dịch TOÀN BỘ, KHÔNG bỏ sót dòng nào.
2. GIỮ NGUYÊN (không dịch):
   - Lệnh Cisco IOS: ip route, router ospf, switchport, show...
   - Tên giao thức viết tắt: OSPF, EIGRP, BGP, RIP, LACP, RSTP, STP, VRRP, HSRP, FHRP, SNMP, FTP, CAPWAP
   - Địa chỉ IP, subnet mask, prefix: 10.0.0.1, 255.255.255.0, /24
   - Tên thiết bị: R1, SW1, PC1, Router1, CPE, NewSW
   - Tên cổng: Gi0/0, Fa0/1, Serial0/3, e0/1
   - Chuẩn IEEE: 802.11a/b/g/n/ac, 802.1X, 802.1Q, WPA2, WPA3, WEP
   - Viết tắt: VLAN, SSID, WLC, AP, PoE, CDP, LLDP, DTP, VTP, STP, BPDU, AES, SHA, RC4, TKIP
   - Tùy chọn: A., B., C., D., E.
   - Answer:, Explanation, Reference:, Note:
   - JSON keys và values kỹ thuật
   - URLs
3. Thuật ngữ chuyên ngành lần đầu: "tiếng Việt (thuật ngữ gốc)"
   Ví dụ: "tầng mạng (Network Layer)", "bảng địa chỉ MAC (MAC address table)"
4. Giữ nguyên xuống dòng (\\n) và khoảng trắng đầu dòng.
5. Trả về ĐÚNG format: [số] bản_dịch (một dòng mỗi kết quả).
6. KHÔNG giải thích, KHÔNG thêm chú thích.

{numbered}"""

def parse_response(raw: str, count: int) -> list[str]:
    pattern = re.compile(r"^\[(\d+)\]\s*(.*)", re.MULTILINE)
    result = [""] * count
    for idx_str, text in pattern.findall(raw):
        idx = int(idx_str)
        if 0 <= idx < count:
            result[idx] = text.strip()
    # Fallback: giữ nguyên nếu không parse được
    for i, v in enumerate(result):
        if not v:
            result[i] = ""
    return result
```

---

## BƯỚC 5 — GHI KẾT QUẢ VÀO XML

### Cho `.docx`:
```python
def set_text_docx(para, new_text: str):
    """Đặt text mới vào paragraph DOCX, giữ format run đầu tiên."""
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    runs = list(para.iter(f"{{{W}}}r"))
    if not runs:
        return
    # Xóa text trong tất cả runs
    for run in runs:
        for t in run.findall(f"{{{W}}}t"):
            run.remove(t)
    # Đặt text mới vào run đầu tiên
    from xml.etree.ElementTree import SubElement
    first_run = runs[0]
    t_elem = SubElement(first_run, f"{{{W}}}t")
    t_elem.text = new_text
    if new_text and (new_text[0] == " " or new_text[-1] == " "):
        t_elem.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
```

### Cho `.odt`:
```python
def set_text_odt(para, new_text: str):
    """Đặt text mới vào paragraph ODT, giữ nguyên draw:frame (ảnh)."""
    DRAW_NS = "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
    # Xóa tất cả children trừ images
    for child in list(para):
        ns = child.tag.split("}")[0].lstrip("{") if "}" in child.tag else ""
        if ns != DRAW_NS:
            para.remove(child)
    para.text = new_text
```

---

## BƯỚC 6 — ĐÓNG GÓI LẠI FILE

```python
import shutil, tempfile

def repack(original_path: str, xml_content: str, xml_filename: str, output_path: str):
    """Tạo file mới với XML đã dịch, giữ nguyên tất cả file khác (ảnh, styles...)."""
    tmpdir = tempfile.mkdtemp()
    
    # Giải nén toàn bộ file gốc
    with zipfile.ZipFile(original_path, "r") as z:
        z.extractall(tmpdir)
    
    # Ghi XML đã dịch
    import os
    with open(os.path.join(tmpdir, xml_filename), "w", encoding="utf-8") as f:
        f.write(xml_content)
    
    # Đóng gói lại
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for dirpath, _, files in os.walk(tmpdir):
            for fname in files:
                fpath = os.path.join(dirpath, fname)
                arcname = os.path.relpath(fpath, tmpdir)
                zout.write(fpath, arcname)
    
    shutil.rmtree(tmpdir)
```

---

## FLOW TỔNG QUÁT

```
input.docx / input.odt
        │
        ▼
  [1] Unzip → lấy content XML
        │
        ▼
  [2] Parse XML → danh sách paragraphs
        │
        ▼
  [3] Filter → chỉ giữ đoạn có text tiếng Anh thực sự
        │
        ▼
  [4] Batch 15 đoạn → gọi AI → nhận bản dịch
        │
        ▼
  [5] Replace text trong XML (giữ nguyên ảnh, format)
        │
        ▼
  [6] Rezip → output_VI.docx / output_VI.odt
```

---

## LƯU Ý QUAN TRỌNG

| Vấn đề | Giải pháp |
|--------|-----------|
| Hình ảnh mất | Không xóa node `draw:frame` hay `wp:inline` |
| Format mất | Chỉ thay text trong `<w:t>`, giữ nguyên `<w:rPr>` |
| Lệnh Cisco bị dịch | Dùng SKIP_PATTERNS để lọc trước khi gửi AI |
| Batch quá lớn | Giới hạn 15 đoạn/lần, sleep 0.5s giữa các batch |
| Text bị split thành nhiều `<w:r>` | Gộp text của tất cả runs trong 1 paragraph trước khi dịch |

---

## SYSTEM PROMPT CHO AI (dùng trong Antigravity)

```
Bạn là chuyên gia dịch tài liệu CCNA từ tiếng Anh sang tiếng Việt.

LUẬT TUYỆT ĐỐI:
- GIỮ NGUYÊN: lệnh Cisco, tên giao thức (OSPF/BGP/EIGRP...), địa chỉ IP/MAC, 
  tên cổng (Gi0/0), chuẩn IEEE (802.1Q), viết tắt (VLAN/SSID/WLC/AP), URLs
- DỊCH: câu hỏi, đáp án, giải thích, mô tả kịch bản
- FORMAT: trả về [số] bản_dịch, giữ nguyên xuống dòng \n
- KHÔNG giải thích thêm
```
