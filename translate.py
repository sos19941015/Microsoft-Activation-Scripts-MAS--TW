import os
import re
import hashlib
import requests
import csv
from deep_translator import GoogleTranslator

# 配置資訊
TARGETS = [
    {
        "name": "CMD",
        "url": "https://raw.githubusercontent.com/massgravel/Microsoft-Activation-Scripts/master/MAS/All-In-One-Version-KL/MAS_AIO.cmd",
        "output": "MAS_AIO_TW.cmd",
        "type": "cmd"
    },
    {
        "name": "PS1",
        "url": "https://raw.githubusercontent.com/massgravel/massgravel.github.io/main/index.html",
        "output": "MAS_AIO_TW.ps1",
        "type": "ps1"
    }
]

HASH_FILE = "hash.txt"
CACHE_FILE = "translation_cache.csv"

def get_remote_content(url):
    """獲取遠端內容並清理 HTML 標籤 (針對 PS1 版)"""
    response = requests.get(url)
    response.raise_for_status()
    raw_content = response.text
    
    if "index.html" in url:
        match = re.search(r'<pre>(.*?)</pre>', raw_content, re.DOTALL | re.IGNORECASE)
        if match:
            clean_content = match.group(1).strip()
        else:
            clean_content = re.sub(r'^.*?<pre>', '', raw_content, flags=re.DOTALL | re.IGNORECASE)
            clean_content = re.sub(r'</pre>.*?$', '', clean_content, flags=re.DOTALL | re.IGNORECASE).strip()
        return hashlib.sha256(clean_content.encode('utf-8')).hexdigest(), clean_content
        
    return hashlib.sha256(response.content).hexdigest(), raw_content

def load_hashes():
    hashes = {}
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r") as f:
            for line in f:
                if ":" in line:
                    k, v = line.strip().split(":", 1)
                    hashes[k] = v
    return hashes

def save_hashes(hashes):
    with open(HASH_FILE, "w") as f:
        for k, v in hashes.items():
            f.write(f"{k}:{v}\n")

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

def protect_text(text, file_type):
    cmd_keywords = [r'\bfind\b', r'\bfindstr\b', r'\bsc\b', r'\breg\b', r'\bping\b', r'\bcls\b', r'\btitle\b', r'\bcolor\b', r'\bmode\b']
    if file_type == "cmd":
        if any(re.search(kw, text, re.I) for kw in cmd_keywords) or any(c in text for c in ['|', '>', '<', '&', '^']):
            return text, [], "", ""
    elif file_type == "ps1":
        ps_cmd = [r'\bInvoke-.*?\b', r'\bGet-.*?\b', r'\bSet-.*?\b', r'\bWrite-.*?\b', r'\bcmd\b', r'\bpowershell\b', r'\|', r'\$']
        if any(re.search(kw, text, re.I) for kw in ps_cmd):
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

    if file_type == "cmd":
        protected = re.sub(r'%\w+?%|!\w+?!|%\~[\w\d:]+|%%\w', add_ph, core_text)
    else: # ps1
        protected = re.sub(r'\$\w+|(?:\$\{.*?\})|\$global:\w+', add_ph, core_text)
    
    terms = ['HWID', 'KMS38', 'KMS', 'Microsoft', 'Windows', 'Office', 'MAS', 'Online', 'ESU', 'Ohook', 'TSforge']
    for t in terms:
        protected = re.sub(rf'\b{t}\b', add_ph, protected)
    
    return protected, placeholders, " "*l_spaces, " "*r_spaces

def normalize_translated(text):
    replacements = {'“': '"', '”': '"', '‘': "'", '’': "'", '（': '(', '）': ')', '：': ':', '；': ';', '％': '%', '！': '!'}
    for old, new in replacements.items(): text = text.replace(old, new)
    return text

def process_content(content, file_type, cache):
    if (file_type == "ps1"):
        # 1. 在開頭加入註解，防止編碼隱形字元破壞第一個語法
        content = "# MAS Traditional Chinese Version\r\n" + content
        
        # 2. 替換下載來源
        new_cmd_url = "https://raw.githubusercontent.com/sos19941015/Microsoft-Activation-Scripts-MAS--TW/main/MAS_AIO_TW.cmd"
        content = re.sub(r'\$URLs = @\(.*?\)', f'$URLs = @(\n        \'{new_cmd_url}\'\n    )', content, flags=re.DOTALL)
        
        # 3. 移除 SHA256 雜湊檢查邏輯 (修正：移除替換字串中多餘的右括號)
        content = re.sub(r'# Verify script integrity.*?return\s+\}', '# 移除雜湊檢查以支援翻譯版本\n', content, flags=re.DOTALL)

    lines = content.splitlines()
    translatable_items = [] 
    processed_lines_with_markers = []
    final_placeholders = {}
    
    marker_counter = 0
    for line in lines:
        processed_line = line
        items_to_process = [] 

        if file_type == "cmd":
            echo_match = re.match(r'^(\s*echo[:\s]\s*)(.*)$', line, re.IGNORECASE)
            if echo_match and not echo_match.group(2).startswith('.'):
                items_to_process.append((echo_match.group(2), echo_match.start(2), echo_match.end(2)))
            if "call :dk_color" in line.lower():
                for m in re.finditer(r'("[^"]*[a-zA-Z]+[^"]*")', line):
                    items_to_process.append((m.group(1).strip('"'), m.start(1)+1, m.end(1)-1))
        else:
            write_match = re.search(r'(Write-Host\s+.*?"|Write-Output\s+.*?")([^"]+)"', line, re.IGNORECASE)
            if write_match:
                items_to_process.append((write_match.group(2), write_match.start(2), write_match.end(2)))
            menu_match = re.search(r'("\s*\[\d+\]\s+)([^"]+)"', line)
            if menu_match:
                items_to_process.append((menu_match.group(2), menu_match.start(2), menu_match.end(2)))

        if items_to_process:
            line_list = list(line)
            for text, start, end in reversed(items_to_process):
                protected, phs, l_sp, r_sp = protect_text(text, file_type)
                if protected == text and not phs: continue

                if protected in cache:
                    trans_text = cache[protected]
                    for p_idx, val in enumerate(phs): trans_text = trans_text.replace(f"__PH_{p_idx}__", val)
                    line_list[start:end] = list(f"{l_sp}{trans_text}{r_sp}")
                else:
                    marker = f"__TRANS_{marker_counter}__"
                    translatable_items.append((protected, phs, l_sp, r_sp, marker_counter))
                    line_list[start:end] = list(marker)
                    marker_counter += 1
            processed_line = "".join(line_list)
        processed_lines_with_markers.append(processed_line)

    if translatable_items:
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
            for p_idx, val in enumerate(phs): trans_text = trans_text.replace(f"__PH_{p_idx}__", val)
            final_placeholders[m_idx] = f"{l_sp}{trans_text}{r_sp}"

    final_lines = []
    inserted_chcp = False
    for line in processed_lines_with_markers:
        final_line = re.sub(r'__TRANS_(\d+)__', lambda m: final_placeholders.get(int(m.group(1)), m.group(0)), line)
        if file_type == "cmd":
            if not inserted_chcp and "@echo off" in final_line.lower():
                final_lines.append(final_line); final_lines.append("chcp 65001 >nul"); inserted_chcp = True
            else: final_lines.append(final_line)
        else: final_lines.append(final_line)

    if file_type == "cmd" and not inserted_chcp: final_lines.insert(0, "chcp 65001 >nul")
    return "\r\n".join(final_lines) + "\r\n"

def main():
    hashes = load_hashes()
    cache = load_cache()
    updated = False
    for target in TARGETS:
        print(f"正在檢查 {target['name']} 更新...")
        try:
            curr_hash, content = get_remote_content(target['url'])
        except Exception as e:
            print(f"下載失敗 {target['name']}: {e}"); continue
        if hashes.get(target['name']) == curr_hash and os.path.exists(target['output']):
            print(f"{target['name']} 無變動。"); continue
        print(f"正在處理 {target['name']}...")
        result = process_content(content, target['type'], cache)
        # PS1 建議不帶 BOM，CMD 建議帶 BOM
        encoding = "utf-8" if target['type'] == "ps1" else "utf-8-sig"
        with open(target['output'], "w", encoding=encoding, newline='') as f: f.write(result)
        hashes[target['name']] = curr_hash
        updated = True
    if updated:
        save_hashes(hashes); save_cache(cache)
        print("所有處理已完成。")
    else: print("沒有任何更新。")

if __name__ == "__main__":
    main()
