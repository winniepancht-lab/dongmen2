import os
import json
from pathlib import Path

data_output = {
    "BOOK_SETTINGS": [],
    "MINUTES_DATABASE": [],
    "DONORS_DATABASE": [],
    "RULES_DATABASE": [],
    "FINANCE_DATABASE": []
}

# 1. 會訊閱讀掃描
issues_dir = Path("issues")
if issues_dir.exists():
    for issue in sorted(issues_dir.iterdir(), reverse=True):
        if issue.is_dir():
            parts = issue.name.split('_')
            if len(parts) >= 2:
                pages = list(issue.glob("page*.*"))
                if pages:
                    ext = pages[0].suffix.strip('.')
                    data_output["BOOK_SETTINGS"].append({
                        "id": issue.name,
                        "title": parts[1],
                        "ext": ext,
                        "totalPages": len(pages),
                        "desc": "點擊封面開始閱讀"
                    })

# 2. 修正後的通用檔案掃描函數
def scan_files(directory, db_list, keys):
    dir_path = Path(directory)
    if dir_path.exists():
        for file in sorted(dir_path.glob("*.*"), reverse=True):
            if file.suffix.lower() in ['.pdf', '.jpg', '.jpeg', '.png']:
                # 只依據設定的 keys 數量來取值，避免因為檔名多打了底線而報錯
                parts = file.stem.split('_')
                entry = {"file": f"../{file.as_posix()}"}
                
                # 依序填入屬性，若檔名部分不足則填入空字串
                for i, key in enumerate(keys):
                    entry[key] = parts[i] if i < len(parts) else ""
                
                db_list.append(entry)

# 掃描各資料夾 (依照您目前實際的檔名習慣修正)
# 會議紀錄：日期_標題.pdf (例: 20250917_114學年度第一次會員代表大會會議紀錄.pdf)
scan_files("files/minutes", data_output["MINUTES_DATABASE"], ["date", "title"])

# 芳名錄：年份_標題_備註.jpg (例: 114-1家長會捐款芳名錄_各項指定捐款_截至20251231.jpg)
scan_files("files/donors", data_output["DONORS_DATABASE"], ["year", "title"])

# 收支明細：學年度_月份_標題.pdf
scan_files("files/finance", data_output["FINANCE_DATABASE"], ["year", "month", "title"])

# 章程：標題.pdf (例: 組織章程.pdf) -> 因為沒有底線，直接取整個檔名為 title
scan_files("files/rules", data_output["RULES_DATABASE"], ["title"])

with open("data.js", "w", encoding="utf-8") as f:
    f.write("// ==========================================\n")
    f.write("// 此檔案由 GitHub Actions 自動生成，請勿手動修改\n")
    f.write("// ==========================================\n\n")
    for key, value in data_output.items():
        js_array = json.dumps(value, ensure_ascii=False, indent=4)
        f.write(f"const {key} = {js_array};\n\n")

print("✅ data.js 已成功重新生成！")
