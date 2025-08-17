import asyncio
import os
import sys
from pathlib import Path
from watcher import Watcher, batch_processor
from utils import log_info, log_error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def main():
    watch_dir = Path(os.path.expanduser("~/Downloads"))
    target_dir = watch_dir
    
    queue = asyncio.Queue()

    log_info("🚀 Starting File Organizer Bot (CLI Mode)")
    log_info(f"📂 Watching directory: {watch_dir}")

    watcher = Watcher(str(watch_dir), str(target_dir), queue)
    watcher.run()

    processor_task = asyncio.create_task(batch_processor(queue, str(target_dir)))

    try:
        await processor_task
    except asyncio.CancelledError:
        log_info("🛑 Processor task cancelled.")
    finally:
        watcher.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_info("\n🛑 Stopped by user.")
    except Exception as e:
        log_error(f"❌ Critical error in main: {e}")
        sys.exit(1)