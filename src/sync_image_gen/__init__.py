import os
import time
import threading
import tkinter as tk
import shutil
import argparse
import base64
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageTk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv
from google import genai
from google.genai import types

class ImageHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            print(f"發現新圖片: {event.src_path}")
            self.callback(event.src_path)

class App:
    def __init__(self, test_mode=False, env_file=None):
        self.root = tk.Tk()
        self.root.title("Sync Image Viewer")
        self.root.configure(background='black')
        self.test_mode = test_mode
        self.env_file = env_file
        
        # 初始載入環境變數
        self.load_config()
        
        self.root.withdraw()
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.root.bind("<Escape>", lambda e: self.hide_window())
        
        self.label = tk.Label(self.root, background='black')
        self.label.pack(expand=True, fill='both')
        
        self.current_photo = None
        
        self.init_client()

    def init_client(self):
        """初始化或重新初始化 Gemini Client"""
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None
            if not self.test_mode:
                print("⚠️ 警告: 尚未設定 GOOGLE_API_KEY。")

    def load_config(self):
        """根據指定路徑或預設路徑載入 .env"""
        loaded = False
        
        # 1. 優先使用手動指定的路徑
        if self.env_file:
            env_path = Path(self.env_file).resolve()
            if env_path.exists():
                load_dotenv(str(env_path), override=True)
                print(f"✅ 已載入指定設定檔: {env_path}")
                loaded = True
            else:
                print(f"❌ 找不到指定的設定檔: {env_path}")

        # 2. 嘗試目前工作目錄下的 .env
        if not loaded:
            cwd_env = Path.cwd() / ".env"
            if cwd_env.exists():
                load_dotenv(str(cwd_env), override=True)
                print(f"✅ 已載入目前目錄設定: {cwd_env}")
                loaded = True

        # 3. 嘗試使用者家目錄下的隱藏設定檔
        if not os.getenv("GOOGLE_API_KEY") and not loaded:
            home_env = Path.home() / ".sync-image-gen.env"
            if home_env.exists():
                load_dotenv(str(home_env), override=True)
                print(f"✅ 已載入全域設定: {home_env}")
                loaded = True

        if not loaded and not self.test_mode and not os.getenv("GOOGLE_API_KEY"):
            print("💡 提示: 在目前目錄建立 .env 檔案或使用 --env-file 指定路徑。")

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
        """呼叫 Nano Banana Pro 進行圖片轉換"""
        self.load_config() # 支援動態更新 Prompt
        
        if not hasattr(self, 'client') or self.client is None:
            self.init_client()
            
        if self.client is None:
            return False

        model_name = os.getenv("GEMINI_MODEL", "gemini-3-pro-image-preview")
        prompt = os.getenv("GEMINI_PROMPT", "Transform this image with a creative style.")
        
        print(f"🚀 使用模型: {model_name}")
        print(f"📝 Prompt: {prompt}")
        
        try:
            raw_img = None
            for _ in range(5):
                try:
                    raw_img = Image.open(image_path)
                    raw_img.load()
                    break
                except:
                    time.sleep(0.5)
            
            if not raw_img:
                return False

            response = self.client.models.generate_content(
                model=model_name,
                contents=[prompt, raw_img],
                config=types.GenerateContentConfig(response_modalities=["IMAGE"])
            )
            
            generated_img_data = None
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        generated_img_data = part.inline_data.data
                        break
            
            if generated_img_data:
                if isinstance(generated_img_data, str):
                    generated_img_data = base64.b64decode(generated_img_data)
                with open(target_path, "wb") as f:
                    f.write(generated_img_data)
                return True
            return False
        except Exception as e:
            print(f"API 錯誤: {e}")
            return False

    def process_and_show(self, image_path):
        output_dir = os.environ.get("OUTPUT_DIRECTORY", "./processed")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        target_path = Path(output_dir) / Path(image_path).name

        time.sleep(0.5)

        if self.test_mode:
            print(f"[測試模式] 顯示圖片")
            shutil.copy2(image_path, target_path)
            self.root.after(0, self.display_image, str(target_path))
        else:
            def run_task():
                success = self.call_gemini_api(image_path, target_path)
                if not success:
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
        
        print(f"🔍 監控中: {watch_dir}")
        try:
            self.root.mainloop()
        finally:
            observer.stop()
            observer.join()

def main():
    parser = argparse.ArgumentParser(description="Sync Image Gen (Nano Banana Pro)")
    parser.add_argument("--watch-dir", type=str, help="監視目錄")
    parser.add_argument("--output-dir", type=str, help="輸出目錄")
    parser.add_argument("--env-file", type=str, help="指定 .env 檔案路徑")
    parser.add_argument("-t", "--test", action="store_true", help="測試模式")
    
    args = parser.parse_args()
    
    app = App(test_mode=args.test, env_file=args.env_file)
    
    # 命令列參數優先權最高
    if args.watch_dir:
        os.environ["WATCH_DIRECTORY"] = args.watch_dir
    elif not os.environ.get("WATCH_DIRECTORY"):
        os.environ["WATCH_DIRECTORY"] = "./images"
        
    if args.output_dir:
        os.environ["OUTPUT_DIRECTORY"] = args.output_dir
    elif not os.environ.get("OUTPUT_DIRECTORY"):
        os.environ["OUTPUT_DIRECTORY"] = "./processed"
    
    app.run()

if __name__ == "__main__":
    main()