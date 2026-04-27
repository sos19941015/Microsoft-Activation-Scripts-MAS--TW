# Microsoft-Activation-Scripts (MAS) 繁體中文自動翻譯版

本專案是一個自動化工具，旨在將官方的 [Microsoft-Activation-Scripts (MAS)](https://github.com/massgravel/Microsoft-Activation-Scripts) 翻譯為繁體中文（台灣），並提供更方便的執行方式。

## 🚀 一鍵執行指令 (PowerShell)

在 PowerShell (系統管理員) 中貼上以下指令即可直接執行：

```powershell
irm https://raw.githubusercontent.com/sos19941015/Microsoft-Activation-Scripts-MAS--TW/main/MAS_AIO_TW.ps1 | iex
```

## ✨ 本專案特色
- **自動化更新**：每日自動監控官方原始碼，一旦原版有更新，本專案會在 24 小時內自動產出對應的中文版。
- **UI 對齊保護**：針對 MAS 特有的色彩指令進行了特殊處理，確保翻譯後選單不跑位、不閃退。
- **雙版本支援**：同時提供 `.cmd` (批次檔) 與 `.ps1` (PowerShell) 的翻譯版本。

## 🙏 感謝與聲明
特別感謝 **[massgravel](https://github.com/massgravel)** 開發了如此強大且純淨的 MAS 工具。

> [!IMPORTANT]
> **免責聲明**：
> - 本專案的程式碼與翻譯內容是由自動化腳本生成，**不保證 100% 準確或安全**。
> - 若執行過程遇到任何錯誤、閃退或不符合預期的行為，請務必執行官方原版指令：
>   `irm https://get.activated.win | iex`
> - 或參考官方儲存庫：[massgravel/Microsoft-Activation-Scripts](https://github.com/massgravel/Microsoft-Activation-Scripts)

## 🛠️ 自行下載
如果您需要下載檔案手動執行，可以從 [Releases](https://github.com/sos19941015/Microsoft-Activation-Scripts-MAS--TW/releases) 頁面獲取最新的：
- `MAS_AIO_TW.cmd`
- `MAS_AIO_TW.ps1`
