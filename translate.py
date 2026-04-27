import os
import re
import hashlib
import requests
from deep_translator import GoogleTranslator

# 配置資訊
SOURCE_URL = "https://raw.githubusercontent.com/massgravel/Microsoft-Activation-Scripts/master/MAS/All-In-One-Version-KL/MAS_AIO.cmd"
HASH_FILE = "hash.txt"
OUTPUT_FILE = "MAS_AIO_TW.cmd"

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

def protect_and_collect(text, collect_list):
    """保護變數並收集需要翻譯的文字"""
    if not text.strip() or not re.search(r'[a-zA-Z]', text):
        return text

    # 保護變數與專有名詞
    placeholders = []
    def add_ph(match):
        placeholders.append(match.group(0))
        return f"__PH_{len(placeholders)-1}__"

    protected = re.sub(r'%\w+?%|!\w+?!|%\~[\w\d:]+|%%\w', add_ph, text)
    terms = ['HWID', 'KMS38', 'KMS', 'Microsoft', 'Windows', 'Office', 'MAS']
    for t in terms:
        protected = re.sub(rf'\b{t}\b', add_ph, protected)

    # 紀錄需要翻譯的文字與其佔位符
    idx = len(collect_list)
    collect_list.append((protected, placeholders))
    return f"__TRANS_{idx}__"

def batch_translate(texts_to_translate):
    """批量翻譯文字"""
    if not texts_to_translate:
        return []
    
    print(f"總共需要翻譯 {len(texts_to_translate)} 條語句...")
    translator = GoogleTranslator(source='auto', target='zh-TW')
    
    # 抽取純文字進行翻譯
    raw_texts = [t[0] for t in texts_to_translate]
    translated_raw = []
    
    # 分批處理 (每批 50 條) 以免 API 超時或限制
    chunk_size = 50
    for i in range(0, len(raw_texts), chunk_size):
        chunk = raw_texts[i:i + chunk_size]
        print(f"正在翻譯第 {i+1} 到 {min(i+chunk_size, len(raw_texts))} 條...")
        try:
            translated_chunk = translator.translate_batch(chunk)
            translated_raw.extend(translated_chunk)
        except Exception as e:
            print(f"批量翻譯錯誤: {e}")
            translated_raw.extend(chunk) # 失敗則保留原文

    # 還原保護標籤
    final_results = []
    for i, trans_text in enumerate(translated_raw):
        placeholders = texts_to_translate[i][1]
        for p_idx, val in enumerate(placeholders):
            trans_text = trans_text.replace(f"__PH_{p_idx}__", val)
        final_results.append(trans_text)
    
    return final_results

def process_cmd_content(content):
    lines = content.splitlines()
    translatable_items = [] # 格式: (protected_text, placeholders)
    processed_lines_with_markers = []
    
    print("正在掃描檔案...")
    for line in lines:
        processed_line = line
        
        # 1. 處理 echo
        echo_match = re.match(r'^(\s*echo\s+)(.*)$', line, re.IGNORECASE)
        if echo_match and not echo_match.group(2).startswith('.'):
            prefix = echo_match.group(1)
            marker = protect_and_collect(echo_match.group(2), translatable_items)
            processed_line = f"{prefix}{marker}"

        # 2. 處理選單 [數字]
        menu_match = re.match(r'^(\s*\[\d+\]\s+)(.*)$', line)
        if menu_match:
            prefix = menu_match.group(1)
            marker = protect_and_collect(menu_match.group(2), translatable_items)
            processed_line = f"{prefix}{marker}"

        # 3. 處理 set /p
        setp_match = re.search(r'(set\s+/p\s+[\w!%]+\s*=\s*")([^"]+)(")', line, re.IGNORECASE)
        if setp_match:
            prefix, text, suffix = setp_match.groups()
            marker = protect_and_collect(text, translatable_items)
            processed_line = f"{prefix}{marker}{suffix}"
        
        # 4. 處理 choice /m
        choice_match = re.search(r'(choice\s+.*?/m\s+")([^"]+)(")', line, re.IGNORECASE)
        if choice_match:
            prefix, text, suffix = choice_match.groups()
            marker = protect_and_collect(text, translatable_items)
            processed_line = f"{prefix}{marker}{suffix}"

        processed_lines_with_markers.append(processed_line)

    # 進行批量翻譯
    translated_results = batch_translate(translatable_items)
    
    # 將翻譯後的內容填回
    final_lines = []
    inserted_chcp = False
    
    for line in processed_lines_with_markers:
        # 尋找並替換翻譯標記 __TRANS_n__
        def replace_marker(match):
            idx = int(match.group(1))
            return translated_results[idx]
        
        final_line = re.sub(r'__TRANS_(\d+)__', replace_marker, line)
        final_lines.append(final_line)
        
        if not inserted_chcp and "@echo off" in final_line.lower():
            final_lines.append("chcp 65001 >nul")
            inserted_chcp = True

    if not inserted_chcp:
        final_lines.insert(0, "chcp 65001 >nul")

    return "\r\n".join(final_lines)

def main():
    print("正在檢查更新...")
    try:
        remote_hash, content = get_remote_hash(SOURCE_URL)
    except Exception as e:
        print(f"錯誤: {e}"); return

    local_hash = read_local_hash()
    if remote_hash == local_hash:
        print("檔案無變動。"); return

    print(f"開始處理新版本...")
    translated_content = process_cmd_content(content)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8-sig") as f:
        f.write(translated_content)
    
    write_local_hash(remote_hash)
    print(f"成功！已儲存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
