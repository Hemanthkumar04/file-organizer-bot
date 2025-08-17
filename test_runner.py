import asyncio
import os
import shutil
from pathlib import Path
import time

# Add src to the Python path to allow imports
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

from watcher import Watcher, batch_processor
from utils import log_info, log_error

# --- Test Configuration ---
TEST_ROOT = Path(__file__).resolve().parent / "test_environment"
WATCH_DIR = TEST_ROOT / "test_watch_folder"
SOURCE_DIR = TEST_ROOT / "test_files" # Corrected from test_files_source
TEST_FILES = [
    "image.jpg", "document.pdf", "archive.zip", "script.py", "unknown.xyz"
]

def setup_test_environment():
    """Cleans and creates a fresh test environment."""
    log_info("--- Setting up test environment ---")
    # Clean the watch folder, but keep the source files
    if WATCH_DIR.exists():
        shutil.rmtree(WATCH_DIR)
    WATCH_DIR.mkdir(parents=True)
    log_info("✅ Test environment is ready.")

def cleanup_test_environment():
    """Removes the test environment folder."""
    log_info("--- Cleaning up test environment ---")
    if TEST_ROOT.exists():
        shutil.rmtree(TEST_ROOT)
    log_info("✅ Cleanup complete.")

async def run_tests():
    """Main function to run the watcher and simulate file operations."""
    setup_test_environment()
    
    queue = asyncio.Queue()
    watcher = Watcher(str(WATCH_DIR), str(WATCH_DIR), queue)
    
    # Start the watcher and the batch processor
    watcher.run()
    processor_task = asyncio.create_task(batch_processor(queue, str(WATCH_DIR)))

    try:
        # --- SCENARIO: BATCH PROCESSING ---
        log_info("\n--- 🧪 TEST: Batch Processing ---")
        log_info(f"Copying all {len(TEST_FILES)} files at once...")
        for filename in TEST_FILES:
            if (SOURCE_DIR / filename).exists():
                shutil.copy(SOURCE_DIR / filename, WATCH_DIR)
        
        log_info("Waiting for the organizer to process the files...")
        await asyncio.sleep(10) # Give the processor time to handle the batch
        
        log_info("\n--- ✅ Automated test complete ---")
        
        log_info("---  Verifying test results ---")
        try:
            # Check if one of the files was moved correctly
            expected_file = WATCH_DIR / "Images" / "image.jpg"
            assert expected_file.exists(), f"Verification failed: {expected_file} was not found!"

            # Check that the original is gone from the root watch folder
            original_file = WATCH_DIR / "image.jpg"
            assert not original_file.exists(), f"Verification failed: {original_file} was not deleted!"

            log_info("✅ Verification successful!")
        except AssertionError as e:
            log_error(f"❌ {e}")
        
    except Exception as e:
        log_error(f"An error occurred during tests: {e}")
    finally:
        log_info("--- Stopping services ---")
        processor_task.cancel()
        watcher.stop()
        await asyncio.sleep(1)
        # You can comment out the cleanup line if you want to inspect the folders after the test
        # cleanup_test_environment() 
        log_info("Test run finished. You can now inspect the 'test_watch_folder'.")


if __name__ == "__main__":
    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        log_info("\n🛑 Test run interrupted by user.")
        cleanup_test_environment()