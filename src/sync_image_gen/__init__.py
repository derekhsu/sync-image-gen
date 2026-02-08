import os
import time
import threading
import tkinter as tk
import shutil
import argparse
from pathlib import Path
from PIL import Image, ImageTk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

class ImageHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            print(f"發現新圖片: {event.src_path}")
            self.callback(event.src_path)

class App:
    def __init__(self, test_mode=False):
        self.root = tk.Tk()
        self.root.title("Sync Image Viewer")
        self.root.configure(background='black')
        self.test_mode = test_mode
        
        # 初始狀態隱藏視窗
        self.root.withdraw()
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.root.bind("<Escape>", lambda e: self.hide_window())
        
        self.label = tk.Label(self.root, background='black')
        self.label.pack(expand=True, fill='both')
        
        self.current_photo = None
        
        # 初始化 Gemini Client
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None
            if not test_mode:
                print("警告: 找不到 GOOGLE_API_KEY，將無法進行圖片轉換。")

    def hide_window(self):
        self.root.attributes("-fullscreen", False)
        self.root.withdraw()
        print("視窗已隱藏，監控中...")

    def display_image(self, image_path):
        try:
            img = Image.open(image_path)
            self.root.deiconify()
            self.root.attributes("-fullscreen", True)
            self.root.attributes("-topmost", True)
            self.root.lift()
            self.root.focus_force()
            
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            img.thumbnail((screen_width, screen_height), Image.Resampling.LANCZOS)
            
            self.current_photo = ImageTk.PhotoImage(img)
            self.label.config(image=self.current_photo)
            self.root.after(1000, lambda: self.root.attributes("-topmost", False))
            print(f"已顯示圖片: {image_path}")
        except Exception as e:
            print(f"顯示圖片失敗: {e}")

    def call_gemini_api(self, image_path, target_path):
        """呼叫 Gemini API 進行圖片轉換"""
        # 強制重新讀取 .env 以取得最新 Prompt
        load_dotenv(override=True)
        
        if not self.client:
            print("錯誤: Gemini Client 未初始化 (缺少 API Key)")
            return False

        # 預設使用 Nano Banana Pro (Gemini 3 Pro Image)
        model_name = os.getenv("GEMINI_MODEL", "gemini-3-pro-image-preview")
        prompt = os.getenv("GEMINI_PROMPT", "Transform this image with a creative style.")
        
        print(f"正在呼叫模型: {model_name}")
        print(f"執行 Prompt: {prompt}")
        
        try:
            # 加入重試機制讀取圖片，防止檔案還在寫入中
            raw_img = None
            for i in range(5):
                try:
                    raw_img = Image.open(image_path)
                    raw_img.load() # 嘗試載入以確保檔案完整
                    break
                except Exception:
                    time.sleep(0.5)
            
            if not raw_img:
                print(f"錯誤: 無法讀取圖片檔案 {image_path}")
                return False
            
            # 使用 Gemini 進行風格轉換
            response = self.client.models.generate_content(
                model=model_name,
                contents=[
                    prompt,
                    raw_img
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                )
            )
            
            # 尋找輸出中的圖片部分
            generated_img = None
            if response.parts:
                for part in response.parts:
                    if part.inline_data:
                        generated_img = part.as_image()
                        break
            
            if generated_img:
                generated_img.save(target_path)
                print(f"Gemini 處理完成: {target_path}")
                return True
            else:
                print(f"Gemini 未回傳圖片數據。")
                if response.text:
                    print(f"回傳文字內容: {response.text}")
                return False
                
        except Exception as e:
            print(f"Gemini API 呼叫失敗: {e}")
            return False

    def process_and_show(self, image_path):
        output_dir = os.environ.get("OUTPUT_DIRECTORY", "./processed")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        target_path = Path(output_dir) / Path(image_path).name

        # 確保檔案已經寫入完成
        time.sleep(0.5)

        if self.test_mode:
            print(f"[測試模式] 複製圖片中: {image_path}")
            time.sleep(0.5)
            shutil.copy2(image_path, target_path)
            self.root.after(0, self.display_image, str(target_path))
        else:
            def run_task():
                success = self.call_gemini_api(image_path, target_path)
                if not success:
                    print("改用原始圖片顯示...")
                    shutil.copy2(image_path, target_path)
                self.root.after(0, self.display_image, str(target_path))
            
            threading.Thread(target=run_task, daemon=True).start()

    def run(self):
        watch_dir = os.environ.get("WATCH_DIRECTORY", "./images")
        Path(watch_dir).mkdir(parents=True, exist_ok=True)
        
        event_handler = ImageHandler(self.process_and_show)
        observer = Observer()
        observer.schedule(event_handler, watch_dir, recursive=False)
        observer.start()
        
        print(f"正在監視目錄: {watch_dir}")
        try:
            self.root.mainloop()
        finally:
            observer.stop()
            observer.join()

def main():
    parser = argparse.ArgumentParser(
        description="Sync Image Gen: 監視目錄、Gemini 圖片處理並全螢幕展示",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--watch-dir", type=str, default=os.getenv("WATCH_DIRECTORY", "./images"))
    parser.add_argument("--output-dir", type=str, default=os.getenv("OUTPUT_DIRECTORY", "./processed"))
    parser.add_argument("-t", "--test", action="store_true")
    
    args = parser.parse_args()
    os.environ["WATCH_DIRECTORY"] = args.watch_dir
    os.environ["OUTPUT_DIRECTORY"] = args.output_dir
    
    app = App(test_mode=args.test)
    app.run()

if __name__ == "__main__":
    main()