import asyncio
from collections import deque
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from organizer import organize_file_async, CATEGORIES
from utils import log_info, log_error

IGNORE_EXTENSIONS = {".crdownload", ".part", ".tmp", ".temp", ".download"}
IGNORE_PREFIXES = {"~$", "."}
DEBOUNCE_TIME = 5
BATCH_MAX_SIZE = 100
BATCH_MAX_WAIT_TIME = 5
RECENT_EVENTS = deque(maxlen=200)

class AsyncFileHandler(FileSystemEventHandler):
    def __init__(self, queue, target_dir, user_exclusions=None):
        self.queue = queue
        self.target_dir = Path(target_dir)
        self.category_folders = {self.target_dir / cat for cat in CATEGORIES.keys()}
        self.user_exclusions = user_exclusions if user_exclusions else set()

    def should_ignore(self, file_path: Path):
        """Check if a file should be ignored."""
        if any(cat in file_path.parents for cat in self.category_folders):
            return True
        
        filename = file_path.name
        suffix = file_path.suffix.lower()

        if suffix in self.user_exclusions:
            return True

        return (
            suffix in IGNORE_EXTENSIONS or
            any(filename.startswith(p) for p in IGNORE_PREFIXES)
        )

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        current_time = time.time()

        for path, timestamp in RECENT_EVENTS:
            if path == file_path and current_time - timestamp < DEBOUNCE_TIME:
                return
        
        if self.should_ignore(file_path):
            log_info(f"⏩ Ignoring file: {file_path.name}")
            return
            
        log_info(f"👀 Detected new file: {file_path.name}")
        RECENT_EVENTS.append((file_path, current_time))
        self.queue.put_nowait(file_path)

class Watcher:
    def __init__(self, watch_dir, target_dir, queue, user_exclusions=None):
        self.watch_dir = watch_dir
        self.target_dir = target_dir
        self.queue = queue
        self.observer = Observer()
        self.event_handler = AsyncFileHandler(self.queue, self.target_dir, user_exclusions)

    def run(self):
        self.observer.schedule(self.event_handler, self.watch_dir, recursive=True)
        self.observer.start()
        log_info(f"👀 Started watching: {self.watch_dir}")

    def stop(self):
        self.observer.stop()
        self.observer.join()
        log_info("🛑 Observer stopped")

async def batch_processor(queue, target_dir):
    """Asynchronously process files from the queue in batches."""
    while True:
        batch = []
        try:
            first_item = await asyncio.wait_for(queue.get(), timeout=BATCH_MAX_WAIT_TIME)
            batch.append(first_item)
            
            while len(batch) < BATCH_MAX_SIZE:
                try:
                    batch.append(queue.get_nowait())
                except asyncio.QueueEmpty:
                    break
        except asyncio.TimeoutError:
            continue

        if batch:
            log_info(f"📦 Processing batch of {len(batch)} files...")
            tasks = [organize_file_async(file_path, Path(target_dir)) for file_path in batch]
            await asyncio.gather(*tasks)
            for _ in batch:
                queue.task_done()