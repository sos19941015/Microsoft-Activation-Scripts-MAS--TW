import os
import re
import requests
from deep_translator import GoogleTranslator

def get_latest_release_info():
    url = "https://api.github.com/repos/massgravel/Microsoft-Activation-Scripts/releases/latest"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    tag_name = data.get("tag_name", "").lstrip("v")
    published_at = data.get("published_at", "").split("T")[0]
    return tag_name, published_at

def get_changelog_content(version):
    url = "https://raw.githubusercontent.com/massgravel/massgrave.dev/main/docs/changelog.md"
    resp = requests.get(url)
    resp.raise_for_status()
    text = resp.text

    # 尋找目標版本的區塊
    # 格式通常是 ## 3.10
    pattern = rf"##\s*{re.escape(version)}\s*\n(.*?)(?=\n##\s*\d+\.\d+|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        content = match.group(1).strip()
        # 移除底線分隔線
        content = re.sub(r"-{10,}", "", content).strip()
        return content
    return "No changelog found for this version."

def translate_text(text):
    if not text or text == "No changelog found for this version.":
        return text
    
    try:
        translator = GoogleTranslator(source='auto', target='zh-TW')
        lines = text.split('\n')
        tr_lines = []
        for line in lines:
            if not line.strip():
                tr_lines.append("")
                continue
            
            # 處理標題
            if line.startswith('#### '):
                tr = translator.translate(line[5:])
                tr_lines.append(f"#### {tr}")
            elif line.startswith('### '):
                tr = translator.translate(line[4:])
                tr_lines.append(f"### {tr}")
            elif line.startswith('## '):
                tr = translator.translate(line[3:])
                tr_lines.append(f"## {tr}")
            elif line.startswith('# '):
                tr = translator.translate(line[2:])
                tr_lines.append(f"# {tr}")
            # 處理清單
            elif line.startswith('- '):
                tr = translator.translate(line[2:])
                tr_lines.append(f"- {tr}")
            # 處理粗體
            elif line.startswith('**') and line.endswith('**'):
                tr = translator.translate(line[2:-2])
                tr_lines.append(f"**{tr}**")
            else:
                tr_lines.append(translator.translate(line))
                
        return '\n'.join(tr_lines)
    except Exception as e:
        print(f"Translation failed: {e}")
        return text

def main():
    print("Fetching latest release info...")
    version, date = get_latest_release_info()
    print(f"Latest version: {version}, Published at: {date}")

    print("Fetching changelog...")
    changelog_en = get_changelog_content(version)
    
    print("Translating changelog...")
    changelog_zh = translate_text(changelog_en)

    notes = f"""## 🤖 自動翻譯版本

本 Release 由 GitHub Actions 自動生成。

**官方原版版本：** {version}
**官方發布日期：** {date}

### 🆕 更新內容 (Changelog)
{changelog_zh}

---

### 📦 包含檔案
| 檔案 | 說明 |
|------|------|
| `MAS_AIO_TW.cmd` | 批次檔版本，雙擊執行 |
| `MAS_AIO_TW.ps1` | PowerShell 載入器 |

### 🚀 一鍵執行（PowerShell 系統管理員）
```powershell
irm https://raw.githubusercontent.com/sos19941015/Microsoft-Activation-Scripts-MAS--TW/main/MAS_AIO_TW.ps1 | iex
```

### ⚠️ 免責聲明
翻譯內容由自動化腳本生成，不保證 100% 準確。如有問題請使用官方原版：`irm https://get.activated.win | iex`

---
*原始專案：[massgravel/Microsoft-Activation-Scripts](https://github.com/massgravel/Microsoft-Activation-Scripts)*
"""

    with open("release_notes.md", "w", encoding="utf-8") as f:
        f.write(notes)
    
    print("release_notes.md generated successfully.")

if __name__ == "__main__":
    main()
