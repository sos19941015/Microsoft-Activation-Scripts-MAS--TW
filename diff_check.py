"""
精確比對：對齊後再比較，找出真正有問題的行。
"""
import re
import requests

URL = "https://raw.githubusercontent.com/massgravel/Microsoft-Activation-Scripts/master/MAS/All-In-One-Version-KL/MAS_AIO.cmd"
print("下載原版...")
r = requests.get(URL, timeout=30)
orig_lines = r.content.decode("utf-8-sig", errors="replace").splitlines()

with open("MAS_AIO_TW.cmd", "r", encoding="utf-8-sig", errors="replace") as f:
    tw_lines = f.read().splitlines()

print(f"原版: {len(orig_lines)} 行  |  翻譯版: {len(tw_lines)} 行")

# ── 找到 chcp 的插入偏移量 ──────────────────────────────────────
# 原版第 1 行是 @echo off，翻譯版第 1 行也是，第 2 行是 chcp
# 所以從第 3 行(idx=2)開始偏移 +1
chcp_offset_start = None
for i, line in enumerate(tw_lines):
    if "chcp 65001" in line.lower():
        chcp_offset_start = i + 1  # chcp 之後開始偏移
        print(f"chcp 65001 插入於翻譯版第 {i+1} 行，之後全部 +1 偏移")
        break

# ── 建立對齊後的配對 ──────────────────────────────────────────
pairs = []
for orig_idx, o in enumerate(orig_lines):
    tw_idx = orig_idx + 1 if (chcp_offset_start and orig_idx + 1 >= chcp_offset_start) else orig_idx
    if tw_idx < len(tw_lines):
        pairs.append((orig_idx + 1, tw_idx + 1, o, tw_lines[tw_idx]))

# ── 分類分析 ─────────────────────────────────────────────────
dangerous = []      # 真正有問題的
echo_changed = []   # echo 行翻譯結果
color_changed = []  # dk_color 行翻譯結果

for orig_lineno, tw_lineno, o, t in pairs:
    if o == t:
        continue
    sl = o.strip().lower()

    is_echo = bool(re.match(r"echo[: ]", sl))
    is_color = "call :dk_color" in sl

    if is_echo:
        echo_changed.append((orig_lineno, tw_lineno, o, t))
    elif is_color:
        color_changed.append((orig_lineno, tw_lineno, o, t))
    else:
        # 非翻譯目標行被改 → 真正的問題
        if o.strip():
            dangerous.append((orig_lineno, tw_lineno, o, t))

print(f"\necho 行翻譯數: {len(echo_changed)}")
print(f"dk_color 行翻譯數: {len(color_changed)}")
print(f"\n=== ⚠️  真正危險問題（非翻譯行被改）: {len(dangerous)} 筆 ===")
for orig_l, tw_l, o, t in dangerous[:25]:
    print(f"  原版L{orig_l} → 翻譯L{tw_l}:")
    print(f"    原: {o[:120]}")
    print(f"    譯: {t[:120]}")
    print()

if not dangerous:
    print("  ✅ 完全沒有問題！所有改動都在 echo/dk_color 行")

# ── 翻譯品質檢查：echo 行 ─────────────────────────────────────
print("\n=== echo 行翻譯品質抽樣（前 15 筆）===")
count = 0
for orig_l, tw_l, o, t in echo_changed:
    if count >= 15:
        break
    o_text = o.strip()
    t_text = t.strip()
    # 略過 echo: 或 echo. 這類空行
    if re.match(r"^echo[:\.]?$", o_text, re.I):
        continue
    print(f"  L{orig_l}: {o_text[:80]}")
    print(f"       → {t_text[:80]}")
    # 警告：變數沒有被保護
    vars_orig = re.findall(r"%\w+%|!\w+!", o)
    vars_trans = re.findall(r"%\w+%|!\w+!", t)
    if set(vars_orig) != set(vars_trans):
        print(f"       ⚠️  變數不一致！原:{vars_orig} 譯:{vars_trans}")
    count += 1

# ── 專項檢查：%mas% 後面跟 URL 的地方 ────────────────────────
print("\n=== 專項：%mas%URL 後綴是否被翻譯（不應被翻譯）===")
bad_mas_urls = []
for orig_l, tw_l, o, t in echo_changed:
    orig_url_parts = re.findall(r'%mas%(\S+)', o)
    trans_url_parts = re.findall(r'%mas%(\S+)', t)
    if orig_url_parts != trans_url_parts:
        bad_mas_urls.append((orig_l, o, t, orig_url_parts, trans_url_parts))
for orig_l, o, t, a, b in bad_mas_urls[:10]:
    print(f"  L{orig_l}: 原={a} → 譯={b}")
    print(f"    原: {o.strip()[:100]}")
    print(f"    譯: {t.strip()[:100]}")
if not bad_mas_urls:
    print("  ✅ 全部 URL 未被翻譯")

# ── 專項檢查：翻譯後出現全形引號 ─────────────────────────────
print("\n=== 專項：翻譯後全形引號檢查 ===")
fullwidth = []
for orig_l, tw_l, o, t in echo_changed + color_changed:
    if any(c in t for c in '\u201c\u201d\u2018\u2019\uff08\uff09'):
        fullwidth.append((orig_l, o, t))
for orig_l, o, t in fullwidth[:5]:
    print(f"  L{orig_l}: {t.strip()[:100]}")
if not fullwidth:
    print("  ✅ 無全形引號")

# ── PS1 結構檢查 ─────────────────────────────────────────────
print("\n=== PS1 翻譯版結構檢查 ===")
with open("MAS_AIO_TW.ps1", "r", encoding="utf-8", errors="replace") as f:
    ps1 = f.read()

# CRLF 問題
crlf_count = ps1.count("\r\n")
lf_only = ps1.count("\n") - crlf_count
print(f"  CRLF 行數: {crlf_count}")
print(f"  LF-only 行數: {lf_only}  {'⚠️  存在 LF-only 行！' if lf_only > 0 else '✅'}")

# URL 替換
if "sos19941015" in ps1:
    print("  ✅ 下載 URL 已替換為自有儲存庫")
else:
    print("  ❌ URL 替換失敗！")

# Hash 移除
if "releaseHash" in ps1:
    print("  ❌ SHA256 雜湊校驗未移除！")
else:
    print("  ✅ SHA256 雜湊校驗已移除")

# 前 3 行
print(f"\n  PS1 前 5 行：")
for i, line in enumerate(ps1.splitlines()[:5], 1):
    print(f"    {i}: {line[:100]}")
