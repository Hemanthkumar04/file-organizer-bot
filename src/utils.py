from pathlib import Path
import logging
import logging.handlers
import sys
import os

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "organizer.log"

logger = logging.getLogger("file-organizer")
logger.setLevel(logging.INFO)

file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=5*1024*1024, backupCount=5, encoding="utf-8"
)
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def log_info(msg: str):
    logger.info(msg)

def log_error(msg: str):
    logger.error(msg)

async def unique_path_async(dest: Path) -> Path:
    """Generate unique filename by appending counter asynchronously."""
    import asyncio
    if not await asyncio.to_thread(dest.exists):
        return dest
        
    counter = 1
    while True:
        new_path = dest.with_name(
            f"{dest.stem} ({counter}){dest.suffix}"
        )
        if not await asyncio.to_thread(new_path.exists):
            return new_path
        counter += 1