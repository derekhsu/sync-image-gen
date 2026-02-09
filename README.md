# Sync Image Gen (Nano Banana Pro)

這是一個基於 Python 的自動化工具，專為目錄監視與 AI 圖片風格轉換而設計。它會監視特定目錄中的新圖片，透過 Google 最新一代的 **Nano Banana Pro (Gemini 3 Pro Image)** 模型進行風格化處理，並將處理後的結果全螢幕展示。

## 🌟 核心功能

- **自動目錄監控**：使用 `watchdog` 實時監控新產生的圖片。
- **Nano Banana Pro 整合**：串接最新 Gemini 3 Pro 影像模型，支援精確的風格轉換（如動漫、賽博龐克等）。
- **跨平台全螢幕展示**：支援 macOS、Ubuntu Desktop 與 Windows，處理完成後自動彈出全螢幕視窗。
- **無干擾模式**：啟動後視窗預設隱藏，僅在有新圖片時彈出；按 `ESC` 隱藏視窗但不結束程式。
- **高度可配置**：透過環境變數或啟動參數靈活調整路徑、Prompt 與模型版本。

## 🚀 快速開始

### 1. 安裝環境
本專案已發佈至 PyPI，您可以選擇以下任一方式安裝：

**使用 uv (推薦)：**
```bash
# 直接執行（免安裝）
uvx sync-image-gen

# 或安裝到全域工具
uv tool install sync-image-gen
```

**使用 pip：**
```bash
pip install sync-image-gen
```

**Ubuntu 使用者注意：**
Linux 系統需額外安裝 tkinter 支持：
```bash
sudo apt-get install python3-tk
```

### 2. 配置環境變數
複製 `.env.example` 並更名為 `.env`，填入您的 API Key：

```bash
cp .env.example .env
```

`.env` 內容說明：
- `GOOGLE_API_KEY`: 您的 Google Gemini API Key。
- `GEMINI_PROMPT`: 轉換圖片的指令（例如：「將圖片轉換為動漫風格」）。
- `GEMINI_MODEL`: 模型名稱（預設為 `gemini-3-pro-image-preview`）。
- `WATCH_DIRECTORY`: 監視路徑。
- `OUTPUT_DIRECTORY`: 處理後圖片儲存路徑。

### 3. 執行程式

**直接執行：**
```bash
sync-image-gen
```

**測試模式（僅複製不呼叫 API）：**
```bash
sync-image-gen -t
```

**使用 uvx 執行（最推薦，保證最新版）：**
```bash
uvx --refresh sync-image-gen
```

## 🛠️ 命令列參數 (CLI Arguments)

啟動參數的優先權高於 `.env` 設定。

| 參數 | 說明 | 預設值 |
| :--- | :--- | :--- |
| `-h, --help` | 顯示說明訊息 | - |
| `--watch-dir` | 指定監視目錄 | `./images` |
| `--output-dir` | 指定處理後圖片儲存目錄 | `./processed` |
| `--env-file` | 指定 `.env` 檔案路徑 | (自動搜尋) |
| `-t, --test` | 啟用測試模式（不呼叫 Gemini API） | `False` |

### 配置搜尋優先順序
程式會依序尋找並載入設定：
1. `--env-file` 指定的路徑。
2. 目前執行指令目錄下的 `.env`。
3. 使用者家目錄下的 `~/.sync-image-gen.env` (適合放 API Key)。

## ⌨️ 快捷鍵

- `ESC`: 隱藏全螢幕視窗（程式繼續在背景監視）。
- `Ctrl + C` (在終端機): 徹底停止程式與監視任務。

## 📋 系統要求

- Python 3.10+
- 穩定且具備 Imagen 功能的 Google Gemini API Key。
- 網路連線（用於呼叫 Gemini API）。
