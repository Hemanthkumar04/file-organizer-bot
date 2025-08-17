import pytest
from pathlib import Path
import asyncio
import sys

# Add the 'src' directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from watcher import AsyncFileHandler

@pytest.fixture
def handler():
    """
    This fixture creates an instance of our AsyncFileHandler for testing.
    We give it a fake queue and a fake target directory.
    """
    queue = asyncio.Queue()
    target_dir = Path("/downloads")
    return AsyncFileHandler(queue, str(target_dir))

# Using pytest.mark.parametrize allows us to run the same test with different inputs.
@pytest.mark.parametrize("file_path, expected", [
    # Files that SHOULD be ignored (expected = True)
    (Path("/downloads/image.crdownload"), True),
    (Path("/downloads/.hiddenfile"), True),
    (Path("/downloads/~$temp.docx"), True),
    (Path("/downloads/Images/photo.jpg"), True), # Already in a category folder

    # Files that should NOT be ignored (expected = False)
    (Path("/downloads/document.pdf"), False),
    (Path("/downloads/archive.zip"), False),
    (Path("/downloads/SUBFOLDER/report.docx"), False),
])
def test_should_ignore(handler, file_path, expected):
    """
    Tests the should_ignore logic with various file types and paths.
    """
    # ARRANGE: The handler and file_path are provided by pytest.
    # ACT: Call the method we are testing.
    result = handler.should_ignore(file_path)
    
    # ASSERT: Check if the result matches what we expected for that input.
    assert result is expected