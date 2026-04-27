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
    if not text.strip() or not re.search(r'[a-zA-Z\u4e00-\u9fa5]', text):
        return text, [], "", ""
    
    # 針對選單對齊，保留開頭和結尾的空格
    l_spaces = len(text) - len(text.lstrip())
    r_spaces = len(text) - len(text.rstrip())
    core_text = text.strip()
    
    placeholders = []
    def add_ph(match):
        placeholders.append(match.group(0))
        return f"__PH_{len(placeholders)-1}__"

    protected = re.sub(r'%\w+?%|!\w+?!|%\~[\w\d:]+|%%\w', add_ph, core_text)
    terms = ['HWID', 'KMS38', 'KMS', 'Microsoft', 'Windows', 'Office', 'MAS', 'Online']
    for t in terms:
        protected = re.sub(rf'\b{t}\b', add_ph, protected)
    
    return protected, placeholders, " "*l_spaces, " "*r_spaces

def process_cmd_content(content):
    lines = content.splitlines()
    cache = load_cache()
    translatable_items = [] 
    processed_lines_with_markers = []
    final_placeholders = {}
    
    print("正在掃描檔案 (包含 UI 指令對齊)...")
    marker_counter = 0
    
    for line in lines:
        processed_line = line
        items_to_process = [] # (original_full_text, start_pos, end_pos)

        # 1. 處理 echo (包含 echo:)
        echo_match = re.match(r'^(\s*echo[:\s]\s*)(.*)$', line, re.IGNORECASE)
        if echo_match and not echo_match.group(2).startswith('.'):
            prefix, text = echo_match.groups()
            items_to_process.append((text, echo_match.start(2), echo_match.end(2)))

        # 2. 處理 call :dk_color 系列 (極度重要)
        # 格式範例: call :dk_color2 %_White% "  [1] " %_Green% "HWID"
        color_matches = re.finditer(r'("[^"]*[a-zA-Z]+[^"]*")', line)
        if "call :dk_color" in line.lower():
            for m in color_matches:
                text = m.group(1).strip('"')
                if len(text) > 1: # 忽略單一符號
                    items_to_process.append((text, m.start(1)+1, m.end(1)-1))
        
        # 3. 處理 set /p 與 choice /m
        setp_match = re.search(r'(set\s+/p\s+[\w!%]+\s*=\s*")([^"]+)(")', line, re.IGNORECASE)
        if setp_match:
            items_to_process.append((setp_match.group(2), setp_match.start(2), setp_match.end(2)))
        
        choice_match = re.search(r'(choice\s+.*?/m\s+")([^"]+)(")', line, re.IGNORECASE)
        if choice_match:
            items_to_process.append((choice_match.group(2), choice_match.start(2), choice_match.end(2)))

        # 執行替換
        if items_to_process:
            # 由後往前替換，避免偏移
            line_list = list(line)
            for text, start, end in reversed(items_to_process):
                protected, phs, l_sp, r_sp = protect_text(text)
                
                if protected in cache:
                    trans_text = cache[protected]
                    for p_idx, val in enumerate(phs):
                        trans_text = trans_text.replace(f"__PH_{p_idx}__", val)
                    res = f"{l_sp}{trans_text}{r_sp}"
                    line_list[start:end] = list(res)
                elif protected == text and not re.search(r'[a-zA-Z]', protected):
                    pass
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
        
        chunk_size = 50
        for i in range(0, len(raw_texts), chunk_size):
            chunk = raw_texts[i:i + chunk_size]
            try:
                res = translator.translate_batch(chunk)
                translated_raw.extend(res)
                for j, tr in enumerate(res): cache[chunk[j]] = tr
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
    return "\r\n".join(final_lines)

def main():
    print("正在檢查更新...")
    try:
        remote_hash, content = get_remote_hash(SOURCE_URL)
    except Exception as e:
        print(f"錯誤: {e}"); return
    
    # 強制重新處理以修正對齊問題
    print(f"開始重新處理並修正 UI 對齊...")
    translated_content = process_cmd_content(content)
    with open(OUTPUT_FILE, "w", encoding="utf-8-sig") as f:
        f.write(translated_content)
    write_local_hash(remote_hash)
    print(f"修正完成！已儲存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
