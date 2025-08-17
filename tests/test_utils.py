import pytest
from pathlib import Path
import sys

# Add the 'src' directory to the Python path so we can import our modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from utils import unique_path_async

# This marker tells pytest to run all tests in this file as asyncio tasks
pytestmark = pytest.mark.asyncio

@pytest.fixture
def temp_dir(tmp_path):
    """
    This is a pytest fixture. It uses the built-in `tmp_path` fixture
    to create a temporary directory for our test to use, so we don't
    mess up our actual file system.
    """
    return tmp_path

async def test_unique_path_for_new_file(temp_dir):
    """
    Tests that the path is returned unchanged if the file does not exist.
    """
    # ARRANGE: Define the path for a file that doesn't exist yet.
    dest_path = temp_dir / "new_file.txt"

    # ACT: Call the function we are testing.
    result = await unique_path_async(dest_path)

    # ASSERT: Check that the result is exactly what we expected.
    assert result == dest_path

async def test_unique_path_for_existing_file(temp_dir):
    """
    Tests that a counter `(1)` is added if the file already exists.
    """
    # ARRANGE: Define a path and create an empty file there.
    dest_path = temp_dir / "existing_file.txt"
    dest_path.touch()

    # ACT: Call the function with the path that now exists.
    result = await unique_path_async(dest_path)

    # ASSERT: Check that the function correctly added the counter.
    expected_path = temp_dir / "existing_file (1).txt"
    assert result == expected_path