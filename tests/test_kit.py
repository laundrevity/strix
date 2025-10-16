from pathlib import Path
import logging

import pytest

from tools.kit import gather_tools


class MockRef:
    """Mock reference object for testing gather_tools"""

    def __init__(self):
        self.log = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_crypto_tool():
    mock_ref = MockRef()
    _, tools = gather_tools(mock_ref)
    assert "get_spot_pair_price" in tools
    tool = tools["get_spot_pair_price"]
    px = await tool("BTC-USD")
    assert px > 0


@pytest.mark.asyncio
async def test_shell_tool():
    mock_ref = MockRef()
    _, tools = gather_tools(mock_ref)
    assert "execute_shell_command" in tools
    tool = tools["execute_shell_command"]
    res = await tool("echo 4")
    assert res["returncode"] == 0
    assert res["stdout"] == "4"
    assert res["stderr"] == ""


def test_edit_tool_create_new_file():
    """Test creating a new file with the edit tool"""
    mock_ref = MockRef()
    _, tools = gather_tools(mock_ref)
    assert "replace" in tools
    edit_tool = tools["replace"]

    # Use the project directory for testing (must be within project root)
    project_dir = Path(__file__).parent.parent
    test_file = project_dir / "test_create_file.txt"

    try:
        # Create new file
        result = edit_tool(
            file_path=str(test_file), old_string="", new_string="Hello World"
        )
        assert result.startswith("Created new file")
        assert test_file.exists()

        # Verify content
        with open(test_file, "r") as f:
            content = f.read()
        assert content == "Hello World"
    finally:
        # Clean up
        if test_file.exists():
            test_file.unlink()


def test_edit_tool_modify_existing_file():
    """Test modifying an existing file with the edit tool"""
    mock_ref = MockRef()
    _, tools = gather_tools(mock_ref)
    assert "replace" in tools
    edit_tool = tools["replace"]

    # Use the project directory for testing (must be within project root)
    project_dir = Path(__file__).parent.parent
    test_file = project_dir / "test_modify_file.txt"

    try:
        # Create initial file with unique content
        with open(test_file, "w") as f:
            f.write("Original content\nThis is line 2\nThis is line 3")

        # Modify existing content with exact match
        result = edit_tool(
            file_path=str(test_file),
            old_string="This is line 2",
            new_string="This is modified line 2",
            expected_replacements=1,
        )
        assert result.startswith("Successfully modified")

        # Verify content
        with open(test_file, "r") as f:
            content = f.read()
        assert "Original content" in content
        assert "This is modified line 2" in content
        assert "This is line 3" in content
        assert "This is line 2" not in content
    finally:
        # Clean up
        if test_file.exists():
            test_file.unlink()


def test_edit_tool_modify_multiple_occurrences():
    """Test modifying multiple occurrences with expected_replacements"""
    mock_ref = MockRef()
    _, tools = gather_tools(mock_ref)
    assert "replace" in tools
    edit_tool = tools["replace"]

    # Use the project directory for testing (must be within project root)
    project_dir = Path(__file__).parent.parent
    test_file = project_dir / "test_multi_file.txt"

    try:
        # Create file with repeated content
        with open(test_file, "w") as f:
            f.write("Hello\nHello\nHello")

        # Modify all 3 occurrences
        result = edit_tool(
            file_path=str(test_file),
            old_string="Hello",
            new_string="Hi",
            expected_replacements=3,
        )
        assert result.startswith("Successfully modified")

        # Verify content
        with open(test_file, "r") as f:
            content = f.read()
        assert content == "Hi\nHi\nHi"
    finally:
        # Clean up
        if test_file.exists():
            test_file.unlink()


def test_edit_tool_error_cases():
    """Test error cases for the edit tool"""
    mock_ref = MockRef()
    _, tools = gather_tools(mock_ref)
    assert "replace" in tools
    edit_tool = tools["replace"]

    # Use the project directory for testing (must be within project root)
    project_dir = Path(__file__).parent.parent

    # Test 1: Attempt to create file that already exists
    existing_file = project_dir / "test_existing_file.txt"
    try:
        with open(existing_file, "w") as f:
            f.write("existing content")

        result = edit_tool(
            file_path=str(existing_file), old_string="", new_string="new content"
        )
        assert "already exists" in result
    finally:
        if existing_file.exists():
            existing_file.unlink()

    # Test 2: Attempt to modify non-existent file
    non_existent_file = project_dir / "nonexistent.txt"
    result = edit_tool(
        file_path=str(non_existent_file), old_string="content", new_string="new content"
    )
    assert "not found" in result

    # Test 3: Attempt to modify string that doesn't exist
    test_file = project_dir / "test_string_file.txt"
    try:
        with open(test_file, "w") as f:
            f.write("Hello World")

        result = edit_tool(
            file_path=str(test_file), old_string="NonExistent", new_string="Replacement"
        )
        assert "could not find the string to replace" in result

        # Test 4: Wrong number of occurrences
        with open(test_file, "w") as f:
            f.write("Hello\nHello\nHello")

        result = edit_tool(
            file_path=str(test_file),
            old_string="Hello",
            new_string="Hi",
            expected_replacements=2,  # But there are 3 occurrences
        )
        assert "expected 2 occurrences but found 3" in result
    finally:
        if test_file.exists():
            test_file.unlink()

    # Test 5: Relative path (should fail)
    relative_file = "test_file.txt"
    result = edit_tool(file_path=relative_file, old_string="", new_string="content")
    assert "must be absolute" in result

    # Test 6: Path outside project root (should fail)
    outside_root = "/tmp/outside_root.txt"
    result = edit_tool(file_path=outside_root, old_string="", new_string="content")
    assert "must be within project root" in result


@pytest.mark.asyncio
async def test_web_search_basic():
    """Test basic web search functionality"""
    mock_ref = MockRef()
    _, tools = gather_tools(mock_ref)
    assert "web_search" in tools
    web_tool = tools["web_search"]

    # Search for a common term
    results = await web_tool("python programming", k=3)

    # Verify structure of results
    assert isinstance(results, list)
    assert len(results) <= 3  # Should return at most k results

    # Check that each result has required fields
    for result in results:
        assert isinstance(result, dict)
        assert "title" in result
        assert "url" in result
        assert "snippet" in result
        assert isinstance(result["title"], str)
        assert isinstance(result["url"], str)
        assert isinstance(result["snippet"], str)
        assert len(result["title"]) > 0
        assert len(result["url"]) > 0
        assert "http" in result["url"]


@pytest.mark.asyncio
async def test_web_search_different_counts():
    """Test web search with different result counts"""
    mock_ref = MockRef()
    _, tools = gather_tools(mock_ref)
    assert "web_search" in tools
    web_tool = tools["web_search"]

    # Test with k=1
    results = await web_tool("test", k=1)
    assert len(results) <= 1

    # Test with k=10 (default is 5)
    results = await web_tool("test", k=10)
    assert len(results) <= 10

    # Test with k=0 (should still return some results, but limited)
    results = await web_tool("test", k=0)
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_web_search_special_sites():
    """Test web search with special site handlers"""
    mock_ref = MockRef()
    _, tools = gather_tools(mock_ref)
    assert "web_search" in tools
    web_tool = tools["web_search"]

    # Test search that might return GitHub results
    results = await web_tool("python asyncio tutorial", k=5)

    # Look for GitHub results in the results
    github_results = [r for r in results if "github.com" in r["url"]]

    # If we found GitHub results, verify they have content
    for github_result in github_results:
        assert len(github_result["snippet"]) > 0
        assert "github.com" in github_result["url"]


@pytest.mark.asyncio
async def test_web_search_error_handling():
    """Test web search error handling"""
    mock_ref = MockRef()
    _, tools = gather_tools(mock_ref)
    assert "web_search" in tools
    web_tool = tools["web_search"]

    # Test with empty query
    results = await web_tool("", k=3)
    assert isinstance(results, list)

    # Test with very long query
    long_query = "x" * 1000
    results = await web_tool(long_query, k=3)
    assert isinstance(results, list)

    # Test with special characters
    special_query = "python +asyncio -tutorial"
    results = await web_tool(special_query, k=3)
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_web_search_debug_mode():
    """Test web search with debug mode enabled"""
    mock_ref = MockRef()
    _, tools = gather_tools(mock_ref)
    assert "web_search" in tools
    web_tool = tools["web_search"]

    # Test with debug=True (this should work without errors)
    results = await web_tool("test search", k=2, debug=True)
    assert isinstance(results, list)
    assert len(results) <= 2

    # Each result should still have required fields
    for result in results:
        assert "title" in result
        assert "url" in result
        assert "snippet" in result
