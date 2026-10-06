import os
import json
from pathlib import Path

# 初始化資料結構
data_output = {
    "BOOK_SETTINGS": [],
    "MINUTES_DATABASE": [],
    "DONORS_DATABASE": [],
    "RULES_DATABASE": [],
    "FINANCE_DATABASE": [] # 新增收支分類
}

# 1. 會訊閱讀 (掃描 issues 資料夾)
# 命名規則：資料夾名稱為「期數_標題」，例如「114-03_第三期 2026.06」
issues_dir = Path("issues")
if issues_dir.exists():
    # 確保依照檔名排序（新期數在前面）
    for issue in sorted(issues_dir.iterdir(), reverse=True):
        if issue.is_dir():
            parts = issue.name.split('_')
            if len(parts) >= 2:
                # 自動計算該資料夾底下有幾張內頁 (page1.jpg, page2.jpg...)
                pages = list(issue.glob("page*.*"))
                if pages:
                    ext = pages[0].suffix.strip('.') # 取得副檔名 (jpg 或 webp)
                    data_output["BOOK_SETTINGS"].append({
                        "id": issue.name,
                        "title": parts[1],
                        "ext": ext,
                        "totalPages": len(pages),
                        "desc": "點擊封面開始閱讀"
                    })

# 2. 通用檔案掃描函數 (會議紀錄、芳名錄、章程、收支)
def scan_files(directory, db_list, expected_parts, keys):
    dir_path = Path(directory)
    if dir_path.exists():
        # 依檔名反向排序，讓最新的檔案排在最前面
        for file in sorted(dir_path.glob("*.*"), reverse=True):
            if file.suffix.lower() in ['.pdf', '.jpg', '.jpeg', '.png']:
                parts = file.stem.split('_')
                if len(parts) >= expected_parts:
                    entry = {"file": f"../{file.as_posix()}"}
                    for i, key in enumerate(keys):
                        entry[key] = parts[i]
                    db_list.append(entry)

# 掃描各資料夾 (命名規則皆使用底線 "_" 分隔)
# 會議紀錄命名：日期_會議類型_分類_標題.pdf (例: 114-10-02_常委會_財務_管樂團指定捐款.pdf)
scan_files("files/minutes", data_output["MINUTES_DATABASE"], 4, ["date", "type", "category", "title"])

# 捐款芳名錄命名：學年度_標題.jpg 或 .pdf (例: 114學年度_直笛隊指定捐款.jpg)
scan_files("files/donors", data_output["DONORS_DATABASE"], 2, ["year", "title"])

# 收支明細命名：學年度_月份_標題.pdf (例: 114學年度_10月_家長會收支結算表.pdf)
scan_files("files/finance", data_output["FINANCE_DATABASE"], 3, ["year", "month", "title"])

# 各式章程命名：分類_標題.pdf (例: 組織章程_家長會組織章程.pdf)
scan_files("files/rules", data_output["RULES_DATABASE"], 2, ["category", "title"])

# 將結果寫入 data.js
with open("data.js", "w", encoding="utf-8") as f:
    f.write("// ==========================================\n")
    f.write("// 此檔案由 GitHub Actions 自動生成，請勿手動修改\n")
    f.write("// ==========================================\n\n")
    for key, value in data_output.items():
        js_array = json.dumps(value, ensure_ascii=False, indent=4)
        f.write(f"const {key} = {js_array};\n\n")

print("✅ data.js 已成功重新生成！")