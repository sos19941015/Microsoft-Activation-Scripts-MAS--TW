# MAS 繁體中文自動翻譯版

> **本專案由自動化腳本生成翻譯，不保證 100% 準確。**  
> 若執行遇到問題，請使用官方原版：`irm https://get.activated.win | iex`

---

## 🚀 一鍵執行（PowerShell 系統管理員）

```powershell
irm https://raw.githubusercontent.com/sos19941015/Microsoft-Activation-Scripts-MAS--TW/main/MAS_AIO_TW.ps1 | iex
```

---

## 📦 手動下載

前往 [Releases 頁面](https://github.com/sos19941015/Microsoft-Activation-Scripts-MAS--TW/releases) 下載最新版：

| 檔案 | 說明 |
|------|------|
| `MAS_AIO_TW.cmd` | 批次檔版本，以系統管理員身分雙擊執行 |
| `MAS_AIO_TW.ps1` | PowerShell 載入器，配合上方 `irm` 指令使用 |

---

## ✨ 專案特色

| 特性 | 說明 |
|------|------|
| 🔄 **自動更新** | 每日 UTC 02:00 監控官方原始碼，有更新立即重新翻譯並發布 Release |
| ⚡ **翻譯快取** | 使用 CSV 翻譯記憶庫，版本微更新時只翻譯差異部分，速度極快 |
| 🛡️ **程式碼保護** | 精確識別並保護所有 Batch 變數（`%var%`、`!var!`）、管道符號、CMD/PS 指令，確保腳本不崩潰 |
| 📝 **詳細日誌** | 每次執行產生 `translate.log`，方便追蹤翻譯過程與除錯 |
| 🌐 **雙格式支援** | 同時翻譯 `.cmd` 批次檔與 `.ps1` PowerShell 載入器 |

---

## 🛠️ 本地執行

```bash
# 安裝相依套件
pip install -r requirements.txt

# 執行翻譯（首次約需 5–10 分鐘，後續因快取只需幾秒）
python translate.py
```

---

## 🙏 致謝

特別感謝 **[massgravel](https://github.com/massgravel)** 開發並維護 [Microsoft-Activation-Scripts](https://github.com/massgravel/Microsoft-Activation-Scripts) 這個強大、純淨的開源工具。

---

## ⚠️ 免責聲明

- 翻譯內容由 Google Translate API 自動產生，**不保證語意完全正確**。
- 本專案僅為學習與研究自動化翻譯流程之用。
- 若執行過程遇到任何錯誤或異常行為，請務必使用官方原版：
  - 執行：`irm https://get.activated.win | iex`
  - 或參考：[massgravel/Microsoft-Activation-Scripts](https://github.com/massgravel/Microsoft-Activation-Scripts)
