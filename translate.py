import os
import re
import hashlib
import requests
import csv
from deep_translator import GoogleTranslator

# 配置資訊
SOURCE_URL = "https://raw.githubusercontent.com/massgravel/Microsoft-Activation-Scripts/master/MAS/All-In-One-Version-KL/MAS_AIO.cmd"
HASH_FILE = "hash.txt"
OUTPUT_FILE = "MAS_AIO_TW.cmd"
CACHE_FILE = "translation_cache.csv"

def get_remote_hash(url):
    response = requests.get(url)
    response.raise_for_status()
    return hashlib.sha256(response.content).hexdigest(), response.text

def read_local_hash():
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r") as f: return f.read().strip()
    return ""

def write_local_hash(sha256_hash):
    with open(HASH_FILE, "w") as f: f.write(sha256_hash)

def load_cache():
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) == 2: cache[row[0]] = row[1]
        except: pass
    return cache

def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8-sig", newline='') as f:
            writer = csv.writer(f)
            for key, value in cache.items(): writer.writerow([key, value])
    except: pass

def protect_text(text):
    # 如果包含指令關鍵字或管道符號，則視為代碼不翻譯
    cmd_keywords = [r'\bfind\b', r'\bfindstr\b', r'\bsc\b', r'\breg\b', r'\bping\b', r'\bcls\b', r'\btitle\b', r'\bcolor\b', r'\bmode\b']
    if any(re.search(kw, text, re.I) for kw in cmd_keywords) or any(c in text for c in ['|', '>', '<', '&', '^']):
        return text, [], "", ""

    if not text.strip() or not re.search(r'[a-zA-Z\u4e00-\u9fa5]', text):
        return text, [], "", ""
    
    l_spaces = len(text) - len(text.lstrip())
    r_spaces = len(text) - len(text.rstrip())
    core_text = text.strip()
    
    placeholders = []
    def add_ph(match):
        placeholders.append(match.group(0))
        return f"__PH_{len(placeholders)-1}__"

    # 保護變數
    protected = re.sub(r'%\w+?%|!\w+?!|%\~[\w\d:]+|%%\w', add_ph, core_text)
    
    # 保護專有名詞
    terms = ['HWID', 'KMS38', 'KMS', 'Microsoft', 'Windows', 'Office', 'MAS', 'Online', 'ESU', 'Ohook', 'TSforge']
    for t in terms:
        protected = re.sub(rf'\b{t}\b', add_ph, protected)
    
    return protected, placeholders, " "*l_spaces, " "*r_spaces

def normalize_translated(text):
    """將翻譯後的非法字元還原"""
    replacements = {
        '“': '"', '”': '"', '‘': "'", '’': "'",
        '（': '(', '）': ')', '：': ':', '；': ';',
        '％': '%', '！': '!'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def process_cmd_content(content):
    lines = content.splitlines()
    cache = load_cache()
    translatable_items = [] 
    processed_lines_with_markers = []
    final_placeholders = {}
    
    print("正在掃描檔案 (嚴格指令過濾模式)...")
    marker_counter = 0
    
    for line in lines:
        processed_line = line
        items_to_process = [] 

        # 1. 處理 echo 顯示內容
        echo_match = re.match(r'^(\s*echo[:\s]\s*)(.*)$', line, re.IGNORECASE)
        if echo_match and not echo_match.group(2).startswith('.'):
            items_to_process.append((echo_match.group(2), echo_match.start(2), echo_match.end(2)))

        # 2. 處理色彩 UI 指令的引號字串
        if "call :dk_color" in line.lower():
            color_matches = re.finditer(r'("[^"]*[a-zA-Z]+[^"]*")', line)
            for m in color_matches:
                text = m.group(1).strip('"')
                if len(text) > 1:
                    items_to_process.append((text, m.start(1)+1, m.end(1)-1))
        
        # 3. 處理提示訊息
        setp_match = re.search(r'(set\s+/p\s+[\w!%]+\s*=\s*")([^"]+)(")', line, re.IGNORECASE)
        if setp_match:
            items_to_process.append((setp_match.group(2), setp_match.start(2), setp_match.end(2)))
        
        choice_match = re.search(r'(choice\s+.*?/m\s+")([^"]+)(")', line, re.IGNORECASE)
        if choice_match:
            items_to_process.append((choice_match.group(2), choice_match.start(2), choice_match.end(2)))

        if items_to_process:
            line_list = list(line)
            for text, start, end in reversed(items_to_process):
                protected, phs, l_sp, r_sp = protect_text(text)
                
                # 如果 protect_text 判斷為指令，protected 會等於 text 且 phs 為空 (或回傳原始內容)
                if protected == text and not phs:
                    continue

                if protected in cache:
                    trans_text = cache[protected]
                    for p_idx, val in enumerate(phs):
                        trans_text = trans_text.replace(f"__PH_{p_idx}__", val)
                    res = f"{l_sp}{trans_text}{r_sp}"
                    line_list[start:end] = list(res)
                else:
                    marker = f"__TRANS_{marker_counter}__"
                    translatable_items.append((protected, phs, l_sp, r_sp, marker_counter))
                    line_list[start:end] = list(marker)
                    marker_counter += 1
            processed_line = "".join(line_list)
        
        processed_lines_with_markers.append(processed_line)

    if translatable_items:
        print(f"需翻譯 {len(translatable_items)} 條新語句...")
        translator = GoogleTranslator(source='auto', target='zh-TW')
        raw_texts = [item[0] for item in translatable_items]
        translated_raw = []
        
        for i in range(0, len(raw_texts), 50):
            chunk = raw_texts[i:i + 50]
            try:
                res = translator.translate_batch(chunk)
                translated_raw.extend([normalize_translated(tr) for tr in res])
                for j, tr in enumerate(res): cache[chunk[j]] = normalize_translated(tr)
            except: translated_raw.extend(chunk)

        for i, (prot, phs, l_sp, r_sp, m_idx) in enumerate(translatable_items):
            trans_text = translated_raw[i]
            for p_idx, val in enumerate(phs):
                trans_text = trans_text.replace(f"__PH_{p_idx}__", val)
            final_placeholders[m_idx] = f"{l_sp}{trans_text}{r_sp}"
        save_cache(cache)

    final_lines = []
    inserted_chcp = False
    for line in processed_lines_with_markers:
        final_line = re.sub(r'__TRANS_(\d+)__', lambda m: final_placeholders.get(int(m.group(1)), m.group(0)), line)
        final_lines.append(final_line)
        if not inserted_chcp and "@echo off" in final_line.lower():
            final_lines.append("chcp 65001 >nul"); inserted_chcp = True

    if not inserted_chcp: final_lines.insert(0, "chcp 65001 >nul")
    return "\r\n".join(final_lines) + "\r\n"

def main():
    print("正在檢查更新...")
    remote_hash, content = get_remote_hash(SOURCE_URL)
    
    # 刪除舊快取中可能受損的項目 (包含全形引號的項目)
    cache = load_cache()
    new_cache = {k: v for k, v in cache.items() if not any(c in v for c in '“”‘’')}
    save_cache(new_cache)

    print(f"重新處理中 (已強化指令保護)...")
    translated_content = process_cmd_content(content)
    with open(OUTPUT_FILE, "w", encoding="utf-8-sig", newline='') as f:
        f.write(translated_content)
    write_local_hash(remote_hash)
    print(f"修正完成！已儲存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
