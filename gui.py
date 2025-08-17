import customtkinter as ctk
from customtkinter import filedialog
import threading
import asyncio
import queue
import logging
from pathlib import Path
import os
import sys
import json

# Add src to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from watcher import Watcher, batch_processor # <<< FIX IS HERE
from organizer import organize_file_async, load_categories_from_file, CONFIG_PATH
from utils import logger

class GuiLogger(logging.Handler):
    """Custom logging handler to redirect logs to the GUI."""
    def __init__(self, text_widget):
        super().__init__()
        self.widget = text_widget
        self.queue = queue.Queue()
        self.widget.after(100, self.poll_log_queue)

    def emit(self, record):
        msg = self.format(record)
        self.queue.put(msg)

    def poll_log_queue(self):
        while True:
            try:
                record = self.queue.get(block=False)
                self.widget.insert(ctk.END, record + '\n')
                self.widget.see(ctk.END) # Auto-scroll to the bottom
            except queue.Empty:
                break
        self.widget.after(100, self.poll_log_queue)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("File Organizer Bot")
        self.geometry("750x600")

        self.bot_thread = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.tab_view.add("Controls")
        self.tab_view.add("Categories")
        self.tab_view.add("Settings")

        self.setup_controls_tab()
        self.setup_categories_tab()
        self.setup_settings_tab()

        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.grid_rowconfigure(1, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        self.log_textbox = ctk.CTkTextbox(log_frame, state="normal", wrap="word")
        self.log_textbox.grid(row=0, column=0, sticky="nsew")

        gui_handler = GuiLogger(self.log_textbox)
        logger.addHandler(gui_handler)
        logger.info("GUI Initialized. Select a folder and press 'Start Bot'.")

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_controls_tab(self):
        controls_tab = self.tab_view.tab("Controls")
        controls_tab.grid_columnconfigure(0, weight=1)

        folder_frame = ctk.CTkFrame(controls_tab)
        folder_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        folder_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(folder_frame, text="Folder to Organize:").grid(row=0, column=0, padx=10, pady=10)
        self.folder_path_entry = ctk.CTkEntry(folder_frame, placeholder_text=str(Path.home() / "Downloads"))
        self.folder_path_entry.insert(0, str(Path.home() / "Downloads"))
        self.folder_path_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(folder_frame, text="Browse...", command=self.select_folder).grid(row=0, column=2, padx=10, pady=10)
        
        control_frame = ctk.CTkFrame(controls_tab)
        control_frame.grid(row=1, column=0, padx=10, pady=0, sticky="ew")
        
        self.start_button = ctk.CTkButton(control_frame, text="Start", command=self.start_bot)
        self.start_button.pack(side="left", padx=5, pady=10)

        self.pause_button = ctk.CTkButton(control_frame, text="Pause", command=self.pause_bot, state="disabled")
        self.pause_button.pack(side="left", padx=5, pady=10)

        self.resume_button = ctk.CTkButton(control_frame, text="Resume", command=self.resume_bot, state="disabled")
        self.resume_button.pack(side="left", padx=5, pady=10)

        self.stop_button = ctk.CTkButton(control_frame, text="Stop", command=self.stop_bot, state="disabled")
        self.stop_button.pack(side="left", padx=5, pady=10)

        self.status_label = ctk.CTkLabel(control_frame, text="Status: Stopped", text_color="gray")
        self.status_label.pack(side="right", padx=10, pady=10)

    def setup_categories_tab(self):
        categories_tab = self.tab_view.tab("Categories")
        categories_tab.grid_columnconfigure(0, weight=1)
        categories_tab.grid_rowconfigure(1, weight=1)

        cat_btn_frame = ctk.CTkFrame(categories_tab)
        cat_btn_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(cat_btn_frame, text="Load from File", command=self.load_categories_to_editor).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(cat_btn_frame, text="Save to File", command=self.save_categories_from_editor).pack(side="left", padx=10, pady=10)
        self.apply_cat_button = ctk.CTkButton(cat_btn_frame, text="Apply Changes", command=self.apply_categories_to_bot)
        self.apply_cat_button.pack(side="left", padx=10, pady=10)
        ctk.CTkLabel(cat_btn_frame, text="(Bot must be stopped to apply changes)", text_color="gray").pack(side="left", padx=10, pady=10)

        self.categories_textbox = ctk.CTkTextbox(categories_tab, wrap="word", font=("Courier New", 12))
        self.categories_textbox.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.load_categories_to_editor()

    def setup_settings_tab(self):
        settings_tab = self.tab_view.tab("Settings")
        settings_tab.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(settings_tab, text="Appearance Mode:").grid(row=0, column=0, padx=20, pady=10, sticky="w")
        self.appearance_menu = ctk.CTkOptionMenu(settings_tab, values=["Light", "Dark", "System"], command=ctk.set_appearance_mode)
        self.appearance_menu.set("Dark")
        self.appearance_menu.grid(row=0, column=1, padx=20, pady=10, sticky="w")
        ctk.CTkLabel(settings_tab, text="Exclude Extensions:").grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.exclusion_entry = ctk.CTkEntry(settings_tab, placeholder_text=".tmp, .log, .bak (comma-separated)")
        self.exclusion_entry.grid(row=1, column=1, padx=20, pady=10, sticky="ew")
    
    def load_categories_to_editor(self):
        try:
            with open(CONFIG_PATH, 'r') as f:
                content = f.read()
                self.categories_textbox.delete("1.0", ctk.END)
                self.categories_textbox.insert("1.0", content)
                logger.info("Loaded categories into editor.")
        except Exception as e:
            logger.error(f"Failed to load categories into editor: {e}")

    def save_categories_from_editor(self):
        try:
            content = self.categories_textbox.get("1.0", ctk.END)
            json.loads(content)
            with open(CONFIG_PATH, 'w') as f:
                f.write(content)
            logger.info("✅ Categories saved to file successfully.")
        except json.JSONDecodeError:
            logger.error("❌ Invalid JSON format. Please correct and save again.")
        except Exception as e:
            logger.error(f"Failed to save categories: {e}")

    def apply_categories_to_bot(self):
        load_categories_from_file()
        logger.info("✅ New categories have been applied to the bot.")

    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.folder_path_entry.delete(0, ctk.END)
            self.folder_path_entry.insert(0, folder_path)
    
    def bot_worker(self, stop_event, pause_event, watch_dir_str, exclusions):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            watch_dir = Path(watch_dir_str)
            if not watch_dir.is_dir():
                logger.error(f"Error: Not a valid directory: {watch_dir}")
                self.after(0, self.stop_bot_on_error)
                return

            file_queue = asyncio.Queue()
            watcher = Watcher(str(watch_dir), str(watch_dir), file_queue, exclusions)
            logger.info(f"🚀 Starting Bot for '{watch_dir}'...")
            watcher.run()

            async def stoppable_batch_processor():
                processor_task = asyncio.create_task(batch_processor(file_queue, str(watch_dir)))
                while not stop_event.is_set():
                    if pause_event.is_set():
                        logger.info("Bot is paused...")
                        while pause_event.is_set() and not stop_event.is_set():
                            await asyncio.sleep(1)
                        if not stop_event.is_set():
                            logger.info("Bot is resumed.")
                    await asyncio.sleep(1)
                
                logger.info("🛑 Stop signal received. Shutting down...")
                processor_task.cancel()
                await asyncio.sleep(1)
                watcher.stop()
                
            loop.run_until_complete(stoppable_batch_processor())
            logger.info("👋 Bot has stopped.")
        except Exception as e:
            logger.error(f"❌ Critical error in bot thread: {e}")
            self.after(0, self.stop_bot_on_error)

    def start_bot(self):
        watch_path = self.folder_path_entry.get()
        if not watch_path or not Path(watch_path).is_dir():
            logger.error("Please select a valid folder before starting.")
            return

        exclusions_str = self.exclusion_entry.get().lower()
        exclusions = {ext.strip() for ext in exclusions_str.split(',') if ext.strip().startswith('.')}
        if exclusions:
            logger.info(f"Excluding extensions: {', '.join(exclusions)}")

        self.stop_event.clear()
        self.pause_event.clear()
        
        self.start_button.configure(state="disabled")
        self.pause_button.configure(state="normal")
        self.resume_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.apply_cat_button.configure(state="disabled")
        self.status_label.configure(text="Status: Running", text_color="green")

        self.bot_thread = threading.Thread(target=self.bot_worker, args=(self.stop_event, self.pause_event, watch_path, exclusions), daemon=True)
        self.bot_thread.start()

    def stop_bot(self, is_error=False):
        self.stop_event.set()
        
        self.start_button.configure(state="normal")
        self.pause_button.configure(state="disabled")
        self.resume_button.configure(state="disabled")
        self.stop_button.configure(state="disabled")
        self.apply_cat_button.configure(state="normal")
        if is_error:
            self.status_label.configure(text="Status: Error!", text_color="red")
        else:
            self.status_label.configure(text="Status: Stopped", text_color="gray")

    def pause_bot(self):
        self.pause_event.set()
        self.pause_button.configure(state="disabled")
        self.resume_button.configure(state="normal")
        self.status_label.configure(text="Status: Paused", text_color="orange")
        logger.info("⏸️ Paused file processing.")
        
    def resume_bot(self):
        self.pause_event.clear()
        self.pause_button.configure(state="normal")
        self.resume_button.configure(state="disabled")
        self.status_label.configure(text="Status: Running", text_color="green")
        logger.info("▶️ Resumed file processing.")

    def stop_bot_on_error(self):
        self.stop_bot(is_error=True)

    def on_closing(self):
        """Handle the window closing event."""
        logger.info("Close button clicked. Shutting down bot...")
        self.stop_event.set()
        # Give the thread a moment to stop
        self.after(500, self.destroy)

if __name__ == "__main__":
    app = App()
    app.mainloop()