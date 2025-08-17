import pytest
import asyncio
import os
from pathlib import Path
import sys

# Add the 'src' directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from organizer import is_file_stable, EXTENSION_MAP

# This marker tells pytest to run all tests in this file as asyncio tasks

def test_extension_map_categorization():
    """
    Tests that the pre-computed EXTENSION_MAP correctly maps extensions to categories.
    """
    # ARRANGE: No setup needed
    # ACT: Access the map
    # ASSERT: Check that common extensions are mapped to the correct category
    assert EXTENSION_MAP['.pdf'] == 'Documents'
    assert EXTENSION_MAP['.jpg'] == 'Images'
    assert EXTENSION_MAP['.zip'] == 'Archives'
    assert EXTENSION_MAP['.mp3'] == 'Audio'
    assert EXTENSION_MAP['.py'] == 'Code'

@pytest.mark.asyncio
async def test_is_file_stable_when_size_is_constant(monkeypatch):
    """
    Tests that is_file_stable returns True if the file size does not change.
    """
    # ARRANGE: We use monkeypatch to replace `os.path.getsize` with a function
    # that always returns the same size (1024 bytes).
    monkeypatch.setattr(os.path, 'getsize', lambda path: 1024)
    
    # ACT: Call the function with a dummy file path.
    # We pass a short interval to make the test run faster.
    result = await is_file_stable(Path("dummy/file.txt"), check_interval=0.01, required_stable_checks=2)
    
    # ASSERT: The result should be True.
    assert result is True

@pytest.mark.asyncio
async def test_is_file_stable_when_size_is_changing(monkeypatch):
    """
    Tests that is_file_stable returns False if the file size keeps changing.
    """
    # ARRANGE: We create a list of sizes that our mock function will return one by one.
    sizes = [100, 200, 300, 400, 500]
    
    # This mock function will pop a size from the list each time it's called.
    def mock_getsize(path):
        return sizes.pop(0)
        
    monkeypatch.setattr(os.path, 'getsize', mock_getsize)
    
    # ACT: Call the function.
    result = await is_file_stable(Path("dummy/file.txt"), check_interval=0.01, required_stable_checks=2)
    
    # ASSERT: The result should be False because the size never stabilized.
    assert result is False