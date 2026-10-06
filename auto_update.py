"""Generate data.js from the static content folders.

Run from dongmen2/ (the GitHub Actions workflow sets that as the working directory).
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "data.js"

ISSUE_META = {
    "114-01": {"title": "創刊號", "date": "2025.11"},
    "114-02": {"title": "第二期", "date": "2026.03"},
    "114-03": {"title": "第三期", "date": "2026.06"},
}
CHINESE_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
MEETING_TYPE = [
    ("常委會", "常", "常委會"),
    ("家長委員會", "家", "家長委員會"),
    ("會員代表大會", "代", "會員代表大會"),
]


def decode_special_name(name: str) -> str:
    """Decode the legacy #UFFFF filename convention, while keeping other text intact."""
    return re.sub(r"#U([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), name)


def url_path(path: Path) -> str:
    return quote("../" + path.relative_to(ROOT).as_posix(), safe="/")


def chinese_number_to_int(value: str) -> int:
    if not value:
        return 0
    if value == "十":
        return 10
    if value.startswith("十"):
        return 10 + CHINESE_NUM.get(value[1:], 0)
    if value.endswith("十"):
        return CHINESE_NUM.get(value[0], 0) * 10
    if "十" in value:
        left, right = value.split("十", 1)
        return CHINESE_NUM.get(left, 0) * 10 + CHINESE_NUM.get(right, 0)
    return CHINESE_NUM.get(value, 0)


def detect_meeting_type(title: str) -> tuple[str, str]:
    for token, key, label in MEETING_TYPE:
        if token in title:
            return key, label
    return "misc", "其他會議"


def scan_newsletters() -> list[dict]:
    output = []
    issues_root = ROOT / "issues"
    if not issues_root.exists():
        return output
    for issue_dir in sorted([p for p in issues_root.iterdir() if p.is_dir()], reverse=True):
        pages = []
        for page in issue_dir.iterdir():
            m = re.fullmatch(r"page-(\d+)\.([A-Za-z0-9]+)", page.name)
            if m:
                pages.append((int(m.group(1)), page))
        pages.sort(key=lambda x: x[0])
        page_numbers = [n for n, _ in pages]
        if page_numbers and page_numbers != list(range(1, len(page_numbers) + 1)):
            print(f"WARNING: page sequence gap in {issue_dir.name}: {page_numbers}")
        cover_candidates = sorted(
            [p for p in issue_dir.iterdir() if p.stem.lower() == "cover" and p.suffix.lower() in {".webp", ".jpg", ".jpeg", ".png"}],
            key=lambda p: p.name,
        )
        if not pages and not cover_candidates:
            continue
        cover = cover_candidates[0] if cover_candidates else None
        meta = ISSUE_META.get(issue_dir.name, {"title": issue_dir.name, "date": ""})
        output.append(
            {
                "id": issue_dir.name,
                "title": meta["title"],
                "date": meta["date"],
                "cover": url_path(cover) if cover else None,
                "pages": [url_path(p) for _, p in pages],
                "pageNumbers": [n for n, _ in pages],
            }
        )
    return output


def scan_minutes() -> list[dict]:
    output = []
    directory = ROOT / "files" / "minutes"
    if not directory.exists():
        return output
    for file in directory.iterdir():
        if file.suffix.lower() != ".pdf":
            continue
        decoded_stem = decode_special_name(file.stem)
        m = re.fullmatch(r"(\d{8})_(.+)", decoded_stem)
        if not m:
            print(f"WARNING: unrecognized minutes filename: {file.name}")
            continue
        date_raw, title = m.groups()
        try:
            dt = datetime.strptime(date_raw, "%Y%m%d")
        except ValueError:
            print(f"WARNING: invalid date in minutes filename: {file.name}")
            continue
        type_key, type_name = detect_meeting_type(title)
        ordinal_match = re.search(r"第([一二三四五六七八九十]+)次", title)
        ordinal = chinese_number_to_int(ordinal_match.group(1)) if ordinal_match else None
        academic_match = re.search(r"(\d{3})學年度", title)
        academic_year = int(academic_match.group(1)) if academic_match else dt.year - 1911
        output.append(
            {
                "date": dt.strftime("%Y-%m-%d"),
                "rocDate": f"{dt.year - 1911}/{dt.month}/{dt.day}",
                "academicYear": academic_year,
                "type": type_key,
                "typeName": type_name,
                "number": ordinal,
                "title": title,
                "file": url_path(file),
            }
        )
    output.sort(key=lambda x: (x["date"], x["type"], x["number"] or 0))
    return output


def scan_donors() -> list[dict]:
    output = []
    directory = ROOT / "files" / "donors"
    if not directory.exists():
        return output
    for file in directory.iterdir():
        if file.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        stem = decode_special_name(file.stem)
        parts = stem.split("_")
        year_code = parts[0].replace("家長會捐款芳名錄", "")
        title_part = parts[1] if len(parts) >= 2 else stem
        title = title_part
        if "廁所香香" in title_part:
            donor_id = "toilet"
            title = "廁所香香專案指定捐款"
        elif "一般會務" in title_part:
            donor_id = "general"
            title = "一般會務捐款"
        elif "各項指定" in title_part:
            donor_id = "misc"
            title = "各項指定捐款"
        else:
            donor_id = re.sub(r"[^a-z0-9-]+", "-", title_part.lower()).strip("-") or "other"
        asof_match = re.search(r"截至(\d{8})", stem)
        asof = ""
        if asof_match:
            asof_dt = datetime.strptime(asof_match.group(1), "%Y%m%d")
            asof = asof_dt.strftime("%Y-%m-%d")
        output.append(
            {
                "id": donor_id,
                "year": f"{year_code}學年度",
                "title": title,
                "file": url_path(file),
                "asOf": asof,
            }
        )
    order = {"general": 0, "toilet": 1, "misc": 2}
    output.sort(key=lambda x: (order.get(x["id"], 99), x["title"]))
    return output


def scan_rules() -> list[dict]:
    output = []
    directory = ROOT / "files" / "rules"
    if not directory.exists():
        return output
    for file in directory.iterdir():
        if file.suffix.lower() != ".pdf":
            continue
        title = decode_special_name(file.stem)
        output.append({"title": title, "file": url_path(file)})
    output.sort(key=lambda x: x["title"])
    return output


def write_js(data: dict) -> None:
    chunks = [
        "// Auto-generated by auto_update.py. Do not edit this file manually.",
        "// Data is rebuilt from issues/ and files/.",
        "",
    ]
    for key, value in data.items():
        chunks.append(f"window.{key} = {json.dumps(value, ensure_ascii=False, indent=2)};")
        chunks.append("")
    OUTPUT.write_text("\n".join(chunks), encoding="utf-8")


if __name__ == "__main__":
    data = {
        "SITE_CONFIG": {
            "siteTitle": "東門國小學生家長會",
            "academicYear": 114,
            "school": "臺北市中正區東門國民小學",
        },
        "BOOK_SETTINGS": scan_newsletters(),
        "MINUTES_DATABASE": scan_minutes(),
        "DONORS_DATABASE": scan_donors(),
        "RULES_DATABASE": scan_rules(),
    }
    write_js(data)
    print(
        f"Generated {OUTPUT.name}: {len(data['BOOK_SETTINGS'])} newsletters, "
        f"{len(data['MINUTES_DATABASE'])} minutes, {len(data['DONORS_DATABASE'])} donor sheets, "
        f"{len(data['RULES_DATABASE'])} rules."
    )
