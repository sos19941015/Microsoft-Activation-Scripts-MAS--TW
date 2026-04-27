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
    """載入翻譯快取"""
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) == 2:
                        cache[row[0]] = row[1]
        except Exception as e:
            print(f"載入快取失敗: {e}")
    return cache

def save_cache(cache):
    """儲存翻譯快取"""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8-sig", newline='') as f:
            writer = csv.writer(f)
            for key, value in cache.items():
                writer.writerow([key, value])
    except Exception as e:
        print(f"儲存快取失敗: {e}")

def protect_text(text):
    """保護變數與專有名詞，傳回 (protected_text, placeholders)"""
    if not text.strip() or not re.search(r'[a-zA-Z]', text):
        return text, []

    placeholders = []
    def add_ph(match):
        placeholders.append(match.group(0))
        return f"__PH_{len(placeholders)-1}__"

    protected = re.sub(r'%\w+?%|!\w+?!|%\~[\w\d:]+|%%\w', add_ph, text)
    terms = ['HWID', 'KMS38', 'KMS', 'Microsoft', 'Windows', 'Office', 'MAS']
    for t in terms:
        protected = re.sub(rf'\b{t}\b', add_ph, protected)
    
    return protected, placeholders

def process_cmd_content(content):
    lines = content.splitlines()
    cache = load_cache()
    
    translatable_items = [] # 格式: (protected_text, placeholders, original_marker_index)
    processed_lines_with_markers = []
    
    # 用來填回最終內容的佔位符列表
    final_placeholders = {} # index -> final_text
    
    print("正在掃描檔案並比對快取...")
    marker_counter = 0
    
    for line in lines:
        processed_line = line
        
        # 匹配模式
        match = None
        prefix, text_to_translate, suffix = "", "", ""
        
        # 1. echo
        echo_match = re.match(r'^(\s*echo\s+)(.*)$', line, re.IGNORECASE)
        if echo_match and not echo_match.group(2).startswith('.'):
            prefix, text_to_translate = echo_match.group(1), echo_match.group(2)
            match = "echo"
        
        # 2. [數字]
        if not match:
            menu_match = re.match(r'^(\s*\[\d+\]\s+)(.*)$', line)
            if menu_match:
                prefix, text_to_translate = menu_match.group(1), menu_match.group(2)
                match = "menu"
        
        # 3. set /p
        if not match:
            setp_match = re.search(r'(set\s+/p\s+[\w!%]+\s*=\s*")([^"]+)(")', line, re.IGNORECASE)
            if setp_match:
                prefix, text_to_translate, suffix = setp_match.groups()
                match = "setp"
        
        # 4. choice /m
        if not match:
            choice_match = re.search(r'(choice\s+.*?/m\s+")([^"]+)(")', line, re.IGNORECASE)
            if choice_match:
                prefix, text_to_translate, suffix = choice_match.groups()
                match = "choice"

        if match:
            protected, phs = protect_text(text_to_translate)
            
            # 檢查快取
            if protected in cache:
                # 從快取還原變數
                trans_text = cache[protected]
                for p_idx, val in enumerate(phs):
                    trans_text = trans_text.replace(f"__PH_{p_idx}__", val)
                processed_line = f"{prefix}{trans_text}{suffix}"
            elif protected == text_to_translate and not re.search(r'[a-zA-Z]', protected):
                # 不需要翻譯
                processed_line = line
            else:
                # 加入翻譯隊列
                marker = f"__TRANS_{marker_counter}__"
                translatable_items.append((protected, phs, marker_counter))
                processed_line = f"{prefix}{marker}{suffix}"
                marker_counter += 1
        
        processed_lines_with_markers.append(processed_line)

    # 執行批量翻譯
    if translatable_items:
        print(f"快取未命中，需翻譯 {len(translatable_items)} 條新語句...")
        translator = GoogleTranslator(source='auto', target='zh-TW')
        raw_texts = [item[0] for item in translatable_items]
        translated_raw = []
        
        chunk_size = 50
        for i in range(0, len(raw_texts), chunk_size):
            chunk = raw_texts[i:i + chunk_size]
            print(f"正在翻譯第 {i+1} 到 {min(i+chunk_size, len(raw_texts))} 條...")
            try:
                translated_chunk = translator.translate_batch(chunk)
                translated_raw.extend(translated_chunk)
                # 更新快取
                for j, trans_res in enumerate(translated_chunk):
                    orig_protected = chunk[j]
                    cache[orig_protected] = trans_res
            except Exception as e:
                print(f"翻譯出錯: {e}")
                translated_raw.extend(chunk)

        # 準備填回資料
        for i, (protected, phs, m_idx) in enumerate(translatable_items):
            trans_text = translated_raw[i]
            # 儲存到快取 (已經在上面存了，這裡確保還原變數後的內容用於輸出)
            for p_idx, val in enumerate(phs):
                trans_text = trans_text.replace(f"__PH_{p_idx}__", val)
            final_placeholders[m_idx] = trans_text
            
        save_cache(cache)
    else:
        print("所有語句皆已從快取中讀取，無需呼叫 API。")

    # 填回內容
    final_lines = []
    inserted_chcp = False
    for line in processed_lines_with_markers:
        def replace_marker(match):
            idx = int(match.group(1))
            return final_placeholders.get(idx, f"__TRANS_{idx}__")
        
        final_line = re.sub(r'__TRANS_(\d+)__', replace_marker, line)
        final_lines.append(final_line)
        if not inserted_chcp and "@echo off" in final_line.lower():
            final_lines.append("chcp 65001 >nul")
            inserted_chcp = True

    if not inserted_chcp: final_lines.insert(0, "chcp 65001 >nul")
    return "\r\n".join(final_lines)

def main():
    print("正在檢查更新...")
    try:
        remote_hash, content = get_remote_hash(SOURCE_URL)
    except Exception as e:
        print(f"錯誤: {e}"); return

    local_hash = read_local_hash()
    if remote_hash == local_hash and os.path.exists(OUTPUT_FILE):
        print("檔案無變動。"); return

    print(f"開始處理版本...")
    translated_content = process_cmd_content(content)
    with open(OUTPUT_FILE, "w", encoding="utf-8-sig") as f:
        f.write(translated_content)
    
    write_local_hash(remote_hash)
    print(f"成功！已儲存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
