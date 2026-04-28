"""
MAS 繁體中文自動翻譯腳本 v2.0
功能：
  - 監控 MAS_AIO.cmd 與官方 PS1 載入器是否更新（Hash 比對）
  - 使用 Google Translate 翻譯可見文字，保護所有程式碼結構
  - 翻譯快取（CSV）加速後續執行
  - 產出符合 Windows CRLF 規範的 UTF-8 檔案
"""

import os
import re
import sys
import csv
import time
import hashlib
import logging
import requests
from deep_translator import GoogleTranslator

# ─────────────────────────────────────────────
# 設定
# ─────────────────────────────────────────────
TARGETS = [
    {
        "name": "CMD",
        "url": "https://raw.githubusercontent.com/massgravel/Microsoft-Activation-Scripts/master/MAS/All-In-One-Version-KL/MAS_AIO.cmd",
        "output": "MAS_AIO_TW.cmd",
        "type": "cmd",
        "encoding": "utf-8-sig",   # BOM 讓 Windows 記事本正確識別
    },
    {
        "name": "PS1",
        "url": "https://raw.githubusercontent.com/massgravel/massgravel.github.io/main/index.html",
        "output": "MAS_AIO_TW.ps1",
        "type": "ps1",
        "encoding": "utf-8",       # 無 BOM，避免 irm | iex 解析失敗
    },
]

HASH_FILE        = "hash.txt"
CACHE_FILE       = "translation_cache.csv"
MY_RAW_BASE      = "https://raw.githubusercontent.com/sos19941015/Microsoft-Activation-Scripts-MAS--TW/main"
BATCH_SIZE       = 30   # 每批翻譯數量（降低至 30 以提高穩定性）
RETRY_LIMIT      = 3    # API 重試次數
RETRY_DELAY      = 2    # 重試間隔（秒）

# ─────────────────────────────────────────────
# Logging 設定
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("translate.log", encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 雜湊與快取 I/O
# ─────────────────────────────────────────────
def load_hashes() -> dict:
    hashes = {}
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if ":" in line:
                    k, v = line.split(":", 1)
                    hashes[k.strip()] = v.strip()
    return hashes

def save_hashes(hashes: dict) -> None:
    with open(HASH_FILE, "w", encoding="utf-8") as f:
        for k, v in hashes.items():
            f.write(f"{k}:{v}\n")

def load_cache() -> dict:
    cache = {}
    if not os.path.exists(CACHE_FILE):
        return cache
    try:
        with open(CACHE_FILE, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.reader(f):
                if len(row) == 2:
                    cache[row[0]] = row[1]
        log.info(f"翻譯快取載入完成，共 {len(cache)} 筆記錄。")
    except Exception as e:
        log.warning(f"載入快取失敗（將從空快取開始）：{e}")
    return cache

def save_cache(cache: dict) -> None:
    with open(CACHE_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        for key, value in cache.items():
            writer.writerow([key, value])
    log.info(f"翻譯快取已儲存，共 {len(cache)} 筆記錄。")

# ─────────────────────────────────────────────
# 下載遠端內容
# ─────────────────────────────────────────────
def get_remote_content(url: str) -> tuple[str, str]:
    """
    回傳 (sha256_hex, text_content)。
    針對 index.html 會自動提取 <pre>...</pre> 內的純 PS1 程式碼。
    """
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    if url.endswith(".html") or "index.html" in url:
        raw = response.text
        match = re.search(r"<pre[^>]*>(.*?)</pre>", raw, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1).strip()
        else:
            # fallback：移除所有 HTML 標籤
            content = re.sub(r"<[^>]+>", "", raw).strip()
        # 還原 HTML 實體
        content = content.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&quot;", '"')
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return sha, content

    sha = hashlib.sha256(response.content).hexdigest()
    return sha, response.text

# ─────────────────────────────────────────────
# 文字保護與還原
# ─────────────────────────────────────────────

# CMD：絕對不翻譯整行的條件
_CMD_SKIP_PATTERNS = re.compile(
    r"""
    [|<>&^]             # 管道、重定向、連結符
    | ^\s*:             # 標籤行 (:label)
    | ^\s*rem\b         # 備註行
    | ^\s*if\b          # if 判斷
    | ^\s*for\b         # for 迴圈
    | ^\s*set\b         # set 指定
    | ^\s*goto\b        # goto
    | ^\s*call\s+:      # call :function（非 dk_color）
    | ^\s*exit\b        # exit
    | ^\s*[a-z]+\.exe\b # 外部可執行檔
    | \bfind\b|\bfindstr\b|\breg\b|\bsc\b|\bwmic\b|\bpowershell\b|\bcmd\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# PS1：整行不翻譯的條件
_PS1_SKIP_PATTERNS = re.compile(
    r"""
    ^\s*\#              # 注釋行
    | ^\s*\$            # 變數賦值開頭
    | [|<>&]            # 管道、重定向
    | \bInvoke-\w+      # Invoke-* cmdlet
    | \bGet-\w+|\bSet-\w+|\bNew-\w+|\bRemove-\w+  # 常見 cmdlet
    | \.(exe|ps1|cmd)\b
    | \bStart-Process\b|\bAdd-Type\b|\bNet\.WebClient\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# 需要保護不被翻譯的專有名詞
_PROTECTED_TERMS = [
    "TSforge", "Ohook", "KMS38", "HWID", "KMS", "ESU",
    "Microsoft", "Windows", "Office", "MAS", "Online", "Retail",
    "Volume", "LTSC", "LTSB", "IoT",
]

def protect_placeholders(text: str, file_type: str) -> tuple[str, list]:
    """
    將變數、專有名詞替換為 __PH_n__ 佔位符，回傳 (protected_text, [原始值列表])。
    """
    placeholders = []

    def store(match):
        placeholders.append(match.group(0))
        return f"__PH_{len(placeholders) - 1}__"

    if file_type == "cmd":
        # %var%, !var!, %~dp0, %%i 等 Batch 變數
        text = re.sub(r"%~[\w\d:]+|%%\w|%\w+%|!\w+!", store, text)
    else:
        # $var, ${var}, $global:var 等 PS 變數
        text = re.sub(r"\$\{[^}]+\}|\$global:\w+|\$\w+", store, text)

    # 保護專有名詞（整詞匹配）
    for term in _PROTECTED_TERMS:
        text = re.sub(rf"\b{re.escape(term)}\b", store, text, flags=re.IGNORECASE)

    return text, placeholders

def restore_placeholders(text: str, placeholders: list) -> str:
    for i, val in enumerate(placeholders):
        text = text.replace(f"__PH_{i}__", val)
    return text

def normalize_quotes(text: str) -> str:
    """將翻譯可能產生的全形標點還原為半形。"""
    table = str.maketrans({
        '\u201c': '"',   # "
        '\u201d': '"',   # "
        '\u2018': "'",   # '
        '\u2019': "'",   # '
        '\uff08': '(',   # （
        '\uff09': ')',   # ）
        '\uff1a': ':',   # ：
        '\uff1b': ';',   # ；
        '\uff05': '%',   # ％
        '\uff01': '!',   # ！
    })
    return text.translate(table)

# ─────────────────────────────────────────────
# 翻譯引擎（含快取 + 重試）
# ─────────────────────────────────────────────
def translate_batch(texts: list[str], cache: dict, translator: GoogleTranslator) -> list[str]:
    """
    批量翻譯，優先使用快取。
    回傳與輸入等長的翻譯結果列表。
    """
    results = [None] * len(texts)
    to_translate_idx = []   # 需要送 API 的索引

    for i, text in enumerate(texts):
        if text in cache:
            results[i] = cache[text]
        else:
            to_translate_idx.append(i)

    if not to_translate_idx:
        return results

    raw_batch = [texts[i] for i in to_translate_idx]
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            translated = translator.translate_batch(raw_batch)
            for j, tr in enumerate(translated):
                orig = raw_batch[j]
                normalized = normalize_quotes(tr) if tr else orig
                cache[orig] = normalized       # 寫入快取
                results[to_translate_idx[j]] = normalized
            return results
        except Exception as e:
            log.warning(f"翻譯 API 第 {attempt}/{RETRY_LIMIT} 次失敗：{e}")
            if attempt < RETRY_LIMIT:
                time.sleep(RETRY_DELAY * attempt)

    # 全部重試失敗 → 保留原文
    log.error("翻譯失敗，保留原文。")
    for j, idx in enumerate(to_translate_idx):
        results[idx] = raw_batch[j]
    return results

# ─────────────────────────────────────────────
# CMD 處理
# ─────────────────────────────────────────────
def should_skip_cmd_line(line: str) -> bool:
    return bool(_CMD_SKIP_PATTERNS.search(line))

def extract_cmd_segments(line: str) -> list[tuple[int, int, str]]:
    """
    從 CMD 行中提取可翻譯的文字片段，回傳 [(start, end, text), ...]。
    """
    segments = []

    # echo 系列（echo:, echo   text, echo.text）
    m = re.match(r"^(\s*echo[: ]\s*)(.+)$", line, re.IGNORECASE)
    if m:
        text = m.group(2).rstrip()
        if text and not re.match(r"^[.\s%!^]*$", text):
            segments.append((m.start(2), m.start(2) + len(text), text))
        return segments  # echo 行只取一段

    # call :dk_color / :dk_color2 / :dk_color3 — 取引號內文字
    if re.search(r"call\s+:dk_color", line, re.IGNORECASE):
        for m in re.finditer(r'"([^"]*[a-zA-Z\u4e00-\u9fff][^"]*)"', line):
            inner = m.group(1)
            start = m.start(1)
            end = m.end(1)
            segments.append((start, end, inner))

    return segments

def process_cmd(content: str, cache: dict) -> str:
    translator = GoogleTranslator(source="auto", target="zh-TW")
    lines = content.splitlines()

    # 第一遍：收集需要翻譯的片段
    pending = []    # [(line_idx, seg_idx, protected_text, placeholders, orig_start, orig_end, leading, trailing)]
    line_segments = [[] for _ in lines]  # 每行的 [(start, end, text)]

    for li, line in enumerate(lines):
        if should_skip_cmd_line(line):
            continue
        segs = extract_cmd_segments(line)
        line_segments[li] = segs
        for start, end, text in segs:
            # 保留首尾空格
            leading  = text[: len(text) - len(text.lstrip())]
            trailing = text[len(text.rstrip()):]
            core = text.strip()
            if not re.search(r"[a-zA-Z]", core):
                continue  # 無英文，不需翻譯
            protected, phs = protect_placeholders(core, "cmd")
            # 若保護後文字與原始相同且無佔位符，可能整段都是不可翻譯的
            if protected == core and not phs and not re.search(r"[a-zA-Z]", core):
                continue
            pending.append((li, start, end, protected, phs, leading, trailing))

    # 第二遍：批量翻譯
    protected_texts = [p[3] for p in pending]
    translated_all  = []
    for i in range(0, len(protected_texts), BATCH_SIZE):
        chunk = protected_texts[i : i + BATCH_SIZE]
        log.info(f"CMD 翻譯進度：{i+1}–{min(i+BATCH_SIZE, len(protected_texts))}/{len(protected_texts)}")
        translated_all.extend(translate_batch(chunk, cache, translator))

    # 第三遍：替換回行內
    line_list = [list(line) for line in lines]
    for idx, (li, start, end, protected, phs, leading, trailing) in enumerate(pending):
        tr = translated_all[idx] if idx < len(translated_all) else protected
        tr = restore_placeholders(tr, phs)
        replacement = leading + tr + trailing
        line_list[li][start:end] = list(replacement)

    # 組合並插入 chcp
    final_lines = []
    inserted_chcp = False
    for chars in line_list:
        line = "".join(chars)
        if not inserted_chcp and re.match(r"\s*@echo\s+off", line, re.IGNORECASE):
            final_lines.append(line)
            final_lines.append("chcp 65001 >nul")
            inserted_chcp = True
        else:
            final_lines.append(line)

    if not inserted_chcp:
        final_lines.insert(0, "chcp 65001 >nul")

    return "\r\n".join(final_lines) + "\r\n"

# ─────────────────────────────────────────────
# PS1 處理
# ─────────────────────────────────────────────
def patch_ps1(content: str) -> str:
    """
    在翻譯前對 PS1 內容做結構性修改：
    1. 替換下載網址為本專案的 CMD 版本
    2. 移除 SHA256 雜湊校驗區塊
    """
    new_cmd_url = f"{MY_RAW_BASE}/MAS_AIO_TW.cmd"

    # 替換 $URLs 陣列（支援單行或多行格式）
    content = re.sub(
        r"\$URLs\s*=\s*@\(.*?\)",
        f"$URLs = @(\n    '{new_cmd_url}'\n)",
        content,
        flags=re.DOTALL,
    )

    # 移除雜湊校驗區塊（從 # Verify... 到對應的 } 結束）
    # 使用非貪婪匹配，僅移除校驗邏輯本身而不影響後續程式碼
    content = re.sub(
        r"#\s*Verify script integrity.*?(?=\n\s*\n|\n\s*[a-zA-Z\$#])",
        "# [已移除雜湊驗證，此版本使用本專案翻譯版 CMD]",
        content,
        flags=re.DOTALL,
    )

    return content

def extract_ps1_segments(line: str) -> list[tuple[int, int, str]]:
    """從 PS1 行中提取可翻譯的字串片段。"""
    if _PS1_SKIP_PATTERNS.search(line):
        return []
    segments = []
    # Write-Host "text" 或 Write-Host 'text'（含 -ForegroundColor 等參數前）
    for m in re.finditer(r'''(?:Write-Host|Write-Output)\s+[^"']*["']([^"']{3,})["']''', line, re.IGNORECASE):
        segments.append((m.start(1), m.end(1), m.group(1)))
    # 純字串行：以引號包裹的獨立文字（選單、說明）
    if not segments:
        for m in re.finditer(r'''["']([a-zA-Z][^"']{5,})["']''', line):
            segments.append((m.start(1), m.end(1), m.group(1)))
    return segments

def process_ps1(content: str, cache: dict) -> str:
    content = patch_ps1(content)
    translator = GoogleTranslator(source="auto", target="zh-TW")
    lines = content.splitlines()

    pending = []
    for li, line in enumerate(lines):
        for start, end, text in extract_ps1_segments(line):
            core = text.strip()
            if not re.search(r"[a-zA-Z]", core) or len(core) < 3:
                continue
            protected, phs = protect_placeholders(core, "ps1")
            pending.append((li, start, end, protected, phs))

    protected_texts = [p[3] for p in pending]
    translated_all = []
    for i in range(0, len(protected_texts), BATCH_SIZE):
        chunk = protected_texts[i : i + BATCH_SIZE]
        log.info(f"PS1 翻譯進度：{i+1}–{min(i+BATCH_SIZE, len(protected_texts))}/{len(protected_texts)}")
        translated_all.extend(translate_batch(chunk, cache, translator))

    line_list = [list(line) for line in lines]
    for idx, (li, start, end, protected, phs) in enumerate(pending):
        tr = translated_all[idx] if idx < len(translated_all) else protected
        tr = restore_placeholders(tr, phs)
        line_list[li][start:end] = list(tr)

    # 加入前導注釋行（確保 irm | iex 時第一個 token 不是關鍵字）
    result_lines = ["# MAS Traditional Chinese Version - Auto Generated"] + ["".join(c) for c in line_list]
    return "\r\n".join(result_lines) + "\r\n"

# ─────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────
PROCESSORS = {
    "cmd": process_cmd,
    "ps1": process_ps1,
}

def main():
    hashes  = load_hashes()
    cache   = load_cache()
    updated = False

    for target in TARGETS:
        name = target["name"]
        log.info(f"── 檢查 {name} 更新 ──")

        try:
            curr_hash, content = get_remote_content(target["url"])
        except Exception as e:
            log.error(f"下載 {name} 失敗：{e}")
            continue

        if hashes.get(name) == curr_hash and os.path.exists(target["output"]):
            log.info(f"{name} 無變動，跳過。")
            continue

        log.info(f"{name} 偵測到更新（或輸出檔不存在），開始處理...")
        processor = PROCESSORS[target["type"]]

        try:
            result = processor(content, cache)
        except Exception as e:
            log.error(f"處理 {name} 時發生錯誤：{e}", exc_info=True)
            continue

        with open(target["output"], "w", encoding=target["encoding"], newline="") as f:
            f.write(result)
        log.info(f"{name} 已寫入 → {target['output']}")

        hashes[name] = curr_hash
        updated = True

    if updated:
        save_hashes(hashes)
        save_cache(cache)
        log.info("全部處理完成。")
        # 讓 GitHub Actions 知道有更新（寫入輸出變數）
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write("updated=true\n")
    else:
        log.info("所有來源均無更新。")
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write("updated=false\n")

if __name__ == "__main__":
    main()
