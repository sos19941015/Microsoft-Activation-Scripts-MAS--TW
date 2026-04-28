"""
深度分析 714 個未翻譯行，按類型分類。
"""
import re
import requests

URL = "https://raw.githubusercontent.com/massgravel/Microsoft-Activation-Scripts/master/MAS/All-In-One-Version-KL/MAS_AIO.cmd"
print("下載原版...")
r = requests.get(URL, timeout=30)
orig_lines = r.content.decode("utf-8-sig", errors="replace").splitlines()

with open("MAS_AIO_TW.cmd", "r", encoding="utf-8-sig", errors="replace") as f:
    tw_lines = f.read().splitlines()

OFFSET = 0
for i, line in enumerate(tw_lines[:20]):
    if "chcp 65001" in line.lower():
        OFFSET = 1
        break

HAS_CHINESE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]')
HAS_ENGLISH = re.compile(r'[a-zA-Z]')
MAS_URL = re.compile(r'%mas%\S*', re.IGNORECASE)

def is_translatable_line(line):
    sl = line.strip()
    sl_low = sl.lower()
    if re.match(r'echo[: ]', sl_low):
        after = re.match(r'echo[: ]\s*(.*)', sl, re.IGNORECASE)
        if after:
            text = after.group(1).strip()
            if not text or re.match(r'^[.\s%!^]*$', text):
                return False
            if not HAS_ENGLISH.search(text):
                return False
            return True
    if 'call :dk_color' in sl_low:
        for m in re.finditer(r'"([^"]*)"', sl):
            if HAS_ENGLISH.search(m.group(1)):
                return True
    return False

def has_meaningful_english(text):
    t = re.sub(r'%\w+%|!\w+!|%~[\w:]+|%%\w', '', text)
    t = re.sub(r'https?://\S+', '', t)
    t = MAS_URL.sub('', t)
    return bool(HAS_ENGLISH.search(t))

# 分類桶
buckets = {
    "dk_color - 完全未翻": [],
    "echo: - 選單行未翻": [],
    "echo 含 | 或 & 被跳過": [],
    "echo 含 find/reg/sc 被跳過": [],
    "dk_color - 全是保護詞": [],
    "其他未翻": [],
}

for orig_idx, orig_line in enumerate(orig_lines):
    tw_idx = orig_idx + OFFSET
    if tw_idx >= len(tw_lines):
        continue
    tw_line = tw_lines[tw_idx]

    if not is_translatable_line(orig_line):
        continue

    sl = orig_line.strip()
    sl_low = sl.lower()

    # 取出文字部分
    if re.match(r'echo[: ]', sl_low):
        m = re.match(r'echo[: ]\s*(.*)', sl, re.IGNORECASE)
        orig_text = m.group(1) if m else ""
    else:
        orig_text = orig_line

    has_zh = HAS_CHINESE.search(tw_line or "")

    if has_zh:
        continue  # 已翻，略過

    # 未翻：分類
    if not has_meaningful_english(orig_text):
        continue  # 合理跳過

    mas_m = MAS_URL.search(orig_text)
    if mas_m:
        prefix = orig_text[:mas_m.start()].strip()
        if not prefix or not HAS_ENGLISH.search(prefix):
            continue  # 合理跳過（只有URL）

    # 分類
    if 'call :dk_color' in sl_low:
        # 檢查引號內是否全是保護詞
        all_protected = True
        for m in re.finditer(r'"([^"]*)"', sl):
            inner = m.group(1)
            cleaned = re.sub(r'%\w+%|!\w+!|%~[\w:]+|%%\w', '', inner)
            cleaned = re.sub(r'\b(HWID|KMS38?|KMS|TSforge|Ohook|MAS|Windows|Office|ESU|Microsoft|Online|Retail|Volume|LTSC|LTSB|IoT)\b', '', cleaned, flags=re.I)
            if HAS_ENGLISH.search(cleaned):
                all_protected = False
        if all_protected:
            buckets["dk_color - 全是保護詞"].append((orig_idx+1, sl))
        else:
            buckets["dk_color - 完全未翻"].append((orig_idx+1, sl))
    elif re.match(r'echo:', sl_low) or re.match(r'echo\s', sl_low):
        if any(c in orig_text for c in ['|', '&&', '^|']):
            buckets["echo 含 | 或 & 被跳過"].append((orig_idx+1, sl))
        elif re.search(r'\b(find|findstr|reg|sc|wmic)\b', orig_text, re.I):
            buckets["echo 含 find/reg/sc 被跳過"].append((orig_idx+1, sl))
        else:
            buckets["echo: - 選單行未翻"].append((orig_idx+1, sl))
    else:
        buckets["其他未翻"].append((orig_idx+1, sl))

print("=" * 60)
print("未翻譯行類型分析")
print("=" * 60)
total_missed = sum(len(v) for v in buckets.values())
for name, items in buckets.items():
    print(f"\n[{len(items):4d}] {name}")
    for lineno, line in items[:5]:
        print(f"        L{lineno}: {line[:100]}")
    if len(items) > 5:
        print(f"        ... 另外 {len(items)-5} 筆")

print(f"\n未翻譯總計: {total_missed}")
