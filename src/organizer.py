import asyncio
import json
from pathlib import Path
from utils import log_info, log_error, unique_path_async
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "categories.json"

CATEGORIES = {}
EXTENSION_MAP = {}

def load_categories_from_file():
    """Loads categories from JSON and populates the global variables."""
    global CATEGORIES, EXTENSION_MAP
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
            categories_data = json.load(f)
            log_info(f"✅ Loaded/Reloaded categories from {CONFIG_PATH}")
    except Exception as e:
        log_error(f"⚠️ Error loading {CONFIG_PATH}: {e}. Using default categories.")
        categories_data = {
            "Images": [".jpg", ".jpeg", ".png", ".gif"],
            "Documents": [".pdf", ".docx", ".txt"],
            "Others": []
        }

    extension_map = {
        ext.lower(): category
        for category, extensions in categories_data.items()
        for ext in extensions
    }
    CATEGORIES = categories_data
    EXTENSION_MAP = extension_map

load_categories_from_file()

async def is_file_stable(file_path, check_interval=1, required_stable_checks=3):
    """Check if file size remains constant over multiple checks asynchronously."""
    last_size = -1
    stable_checks = 0
    
    for _ in range(required_stable_checks * 2):
        try:
            current_size = await asyncio.to_thread(os.path.getsize, file_path)
            if current_size == last_size:
                stable_checks += 1
            else:
                stable_checks = 0
            last_size = current_size
            
            if stable_checks >= required_stable_checks:
                return True
                
        except FileNotFoundError:
            await asyncio.sleep(check_interval)
        except Exception as e:
            log_error(f"⚠️ Error checking file stability for {file_path}: {e}")
            return False
        
        await asyncio.sleep(check_interval)

    return False

async def organize_file_async(file_path: Path, target_dir: Path):
    """Move a file into its categorized folder asynchronously."""
    log_info(f"🔍 Processing file: {file_path.name}")

    if not await asyncio.to_thread(file_path.exists) or await asyncio.to_thread(file_path.is_dir):
        return

    if not await is_file_stable(file_path):
        log_error(f"⚠️ File not stable, skipping: {file_path.name}")
        return

    ext = file_path.suffix.lower()
    category = EXTENSION_MAP.get(ext, "Others")
    log_info(f"📂 Categorized '{file_path.name}' as: {category}")

    category_dir = target_dir / category
    await asyncio.to_thread(category_dir.mkdir, exist_ok=True)

    dest_path = await unique_path_async(category_dir / file_path.name)
    
    try:
        await asyncio.to_thread(os.rename, file_path, dest_path)
        log_info(f"✅ Moved to: {dest_path}")
    except Exception as e:
        log_error(f"❌ Failed to move {file_path}: {e}")