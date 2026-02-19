import os
import pytest
import unittest.mock
from unittest.mock import MagicMock, patch
from tool_monitor import tools
from tool_monitor.tools import (
    _tool_search, 
    _tool_file_write,
    _secure_tool_file_write,
    _tool_summarize
)

# ---------------------------------------------------------------------------
# Generator/API Handling Tests
# ---------------------------------------------------------------------------

@patch("ddgs.DDGS")
def test_tool_search_success(mock_ddgs_cls):
    # Mock the generator response
    mock_instance = mock_ddgs_cls.return_value
    mock_instance.text.return_value = [
        {"title": "Result 1", "body": "Body 1", "href": "http://1.com"}
    ]
    
    result = _tool_search({"query": "test"})
    assert "Result 1" in result
    assert "Body 1" in result
    assert "http://1.com" in result

@patch("ddgs.DDGS")
def test_tool_search_empty_query(mock_ddgs_cls):
    result = _tool_search({"query": "   "})
    assert "Error: no query provided" in result
    mock_ddgs_cls.assert_not_called()

@patch("ddgs.DDGS")
def test_tool_search_no_results(mock_ddgs_cls):
    mock_instance = mock_ddgs_cls.return_value
    mock_instance.text.return_value = []
    
    result = _tool_search({"query": "ghost"})
    assert "No results found" in result

@patch("ddgs.DDGS")
def test_tool_search_exception(mock_ddgs_cls):
    mock_instance = mock_ddgs_cls.return_value
    # Generator raises exception when iterated? 
    # Or call to .text raises?
    mock_instance.text.side_effect = Exception("Network timeout")
    
    result = _tool_search({"query": "crash"})
    assert "Search failed: Network timeout" in result

# ---------------------------------------------------------------------------
# Security Sandboxing Tests
# ---------------------------------------------------------------------------

def test_tool_summarize_truncation():
    text = "a" * 5000
    result = _tool_summarize({"text": text})
    assert len(result) == 4000

def test_file_write_path_traversal(tmp_path):
    """
    Test the currently active _tool_file_write for path traversal vulnerability.
    If the function is insecure (as suspected), this test will pass if we assert success,
    or fail if we assert security.
    """
    
    # 1. Test the INSECURE tool (confirming vulnerability)
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        
        # Attack: Attempt to write outside the current directory
        # ../vulnerable.txt
        # If _tool_file_write is insecure, this succeeds.
        target_file = tmp_path.parent / "vulnerable.txt"
        args = {"path": "../vulnerable.txt", "content": "exploit"}
        
        # We demonstrate here that the existing tool IS insecure.
        # This test ensures we have visibility on the vulnerability.
        result = _tool_file_write(args)
        assert "Wrote" in result
        assert target_file.exists()
        
        # Clean up
        target_file.unlink()
        
        # 2. Test _secure_tool_file_write (The correct implementation)
        # Create a workspace dir
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        
        # Attempt traversal out of workspace
        args_traversal = {"path": "../outside.txt", "content": "hack"}
        result = _secure_tool_file_write(args_traversal)
        
        assert "SECURITY BLOCK" in result
        assert not (tmp_path / "outside.txt").exists()
        
        # 3. Test valid write in workspace
        args_valid = {"path": "safe.txt", "content": "ok"}
        result_valid = _secure_tool_file_write(args_valid)
        assert "Wrote" in result_valid
        assert (workspace / "safe.txt").exists()
        
    finally:
        os.chdir(cwd)
