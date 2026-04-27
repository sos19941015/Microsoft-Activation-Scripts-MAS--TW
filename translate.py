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
    """獲取遠端檔案的 SHA256 Hash"""
    response = requests.get(url)
    response.raise_for_status()
    content = response.content
    sha256_hash = hashlib.sha256(content).hexdigest()
    return sha256_hash, response.text

def read_local_hash():
    """讀取本地儲存的 Hash"""
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r") as f:
            return f.read().strip()
    return ""

def write_local_hash(sha256_hash):
    """更新本地 Hash 紀錄"""
    with open(HASH_FILE, "w") as f:
        f.write(sha256_hash)

def translate_text(text):
    """翻譯文字，保留變數與特定格式"""
    if not text.strip() or re.match(r'^[\s\.]*$', text):
        return text

    # 保護機制：將不需要翻譯的內容替換為暫存標籤
    placeholders = []
    def add_placeholder(match):
        placeholders.append(match.group(0))
        return f"__PH_{len(placeholders)-1}__"

    # 1. 保護變數模式 (例如 %var%, !var!, %~dp0, %%i)
    protected_text = re.sub(r'%\w+?%|!\w+?!|%\~[\w\d:]+|%%\w', add_placeholder, text)
    
    # 2. 保護專有名詞 (不希望被翻譯成中文的術語)
    protected_terms = ['HWID', 'KMS38', 'KMS', 'Microsoft', 'Windows', 'Office', 'MAS']
    for term in protected_terms:
        protected_text = re.sub(rf'\b{term}\b', add_placeholder, protected_text)

    try:
        # 只有在包含字母或中文字元時才進行翻譯
        if not re.search(r'[a-zA-Z]', protected_text):
            return text
            
        translated = GoogleTranslator(source='auto', target='zh-TW').translate(protected_text)
        
        # 還原所有標籤
        for i, val in enumerate(placeholders):
            translated = translated.replace(f"__PH_{i}__", val)
        return translated
    except Exception as e:
        print(f"翻譯出錯: {e}")
        return text

def process_cmd_content(content):
    """解析並翻譯 CMD 內容"""
    lines = content.splitlines()
    new_lines = []
    
    # 插入 chcp 65001 >nul 在 @echo off 之後或檔案最前面
    inserted_chcp = False
    
    for line in lines:
        processed_line = line
        
        # 處理 echo 指令
        # 匹配模式：echo 內容 (忽略 echo. 或單純的 echo)
        echo_match = re.match(r'^(\s*echo\s+)(.*)$', line, re.IGNORECASE)
        if echo_match and not echo_match.group(2).startswith('.'):
            prefix = echo_match.group(1)
            text_to_translate = echo_match.group(2)
            # 如果是單純的符號或空行則不翻譯
            if re.search(r'[a-zA-Z\u4e00-\u9fa5]', text_to_translate):
                translated = translate_text(text_to_translate)
                processed_line = f"{prefix}{translated}"

        # 處理選單文字
        # 匹配模式：[數字] 說明文字
        menu_match = re.match(r'^(\s*\[\d+\]\s+)(.*)$', line)
        if menu_match:
            prefix = menu_match.group(1)
            text_to_translate = menu_match.group(2)
            translated = translate_text(text_to_translate)
            processed_line = f"{prefix}{translated}"

        # 處理 set /p 提示訊息
        setp_match = re.search(r'(set\s+/p\s+[\w!%]+\s*=\s*")([^"]+)(")', line, re.IGNORECASE)
        if setp_match:
            prefix, text_to_translate, suffix = setp_match.groups()
            translated = translate_text(text_to_translate)
            processed_line = f"{prefix}{translated}{suffix}"
        elif re.search(r'set\s+/p\s+[\w!%]+\s*=\s*([^"\s].*)', line, re.IGNORECASE):
            # 處理沒有引號的 set /p
            setp_match_no_quotes = re.search(r'(set\s+/p\s+[\w!%]+\s*=\s*)(.*)', line, re.IGNORECASE)
            prefix, text_to_translate = setp_match_no_quotes.groups()
            translated = translate_text(text_to_translate)
            processed_line = f"{prefix}{translated}"

        # 處理 choice /m 提示訊息
        choice_match = re.search(r'(choice\s+.*?/m\s+")([^"]+)(")', line, re.IGNORECASE)
        if choice_match:
            prefix, text_to_translate, suffix = choice_match.groups()
            translated = translate_text(text_to_translate)
            processed_line = f"{prefix}{translated}{suffix}"

        new_lines.append(processed_line)
        
        # 在 @echo off 之後插入編碼設定
        if not inserted_chcp and "@echo off" in line.lower():
            new_lines.append("chcp 65001 >nul")
            inserted_chcp = True

    # 如果沒找到 @echo off，在最前面補上
    if not inserted_chcp:
        new_lines.insert(0, "chcp 65001 >nul")

    return "\r\n".join(new_lines)

def main():
    print("正在檢查更新...")
    try:
        remote_hash, content = get_remote_hash(SOURCE_URL)
    except Exception as e:
        print(f"無法獲取遠端檔案: {e}")
        return

    local_hash = read_local_hash()

    if remote_hash == local_hash:
        print("檔案無變動，結束程式。")
        return

    print(f"偵測到新版本 (Hash: {remote_hash[:8]})，開始處理...")
    
    translated_content = process_cmd_content(content)
    
    # 以 UTF-8 with BOM (utf-8-sig) 儲存
    with open(OUTPUT_FILE, "w", encoding="utf-8-sig") as f:
        f.write(translated_content)
    
    write_local_hash(remote_hash)
    print(f"處理完成！已儲存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
