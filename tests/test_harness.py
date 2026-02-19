import json
import pytest
from unittest.mock import MagicMock, patch
from tool_monitor import harness
from tool_monitor.harness import (
    Scaffold, 
    IntegrityError, 
    ToolNotFoundError, 
    PlanParseError, 
    ReACTParseError,
    _parse_react_response
)
from tool_monitor.models import Plan, Step, ExecutionRecord
from tool_monitor.merkle import MerkleTree

# ---------------------------------------------------------------------------
# Merkle Tree Verification Tests
# ---------------------------------------------------------------------------

def test_merkle_tree_construction_and_verification():
    step1 = Step(id=1, tool="echo", args={"message": "hello"}, description="say hello")
    step2 = Step(id=2, tool="search", args={"query": "test"}, description="search test")
    
    plan_steps = [step1.model_dump(), step2.model_dump()]
    tree = MerkleTree(plan_steps)
    
    # Verify both leaves match
    assert tree.verify_leaf(0, step1.model_dump()) is True
    assert tree.verify_leaf(1, step2.model_dump()) is True
    
    # Verify mismatch fails
    mutated_step = step1.model_dump()
    mutated_step["tool"] = "hacked_tool"
    assert tree.verify_leaf(0, mutated_step) is False

def test_merkle_tree_empty_steps():
    with pytest.raises(ValueError, match="empty step list"):
        MerkleTree([])

# ---------------------------------------------------------------------------
# Parser Resilience Tests
# ---------------------------------------------------------------------------

def test_parse_react_response_valid():
    response = """Thought: Let's search for python.
Action: search
Args: {"query": "python"}"""
    thought, action, args = _parse_react_response(response)
    assert thought == "Let's search for python."
    assert action == "search"
    assert args == {"query": "python"}

@pytest.mark.xfail(reason="Bug in regex: Args capture group expects start with '{', failing on markdown blocks")
def test_parse_react_response_markdown_json():
    response = """Thought: I will write to a file.
Action: file_write
Args: ```json
{
    "path": "test.txt",
    "content": "hello"
}
```"""
    thought, action, args = _parse_react_response(response)
    assert args == {"path": "test.txt", "content": "hello"}

def test_parse_react_response_malformed_json():
    response = """Thought: Invalid JSON here.
Action: echo
Args: {broken: json}"""
    with pytest.raises(ReACTParseError):
        _parse_react_response(response)

def test_parse_react_response_missing_fields():
    response = "Just some text without format."
    with pytest.raises(ReACTParseError):
        _parse_react_response(response)

def test_parse_plan_valid():
    scaffold = Scaffold("user", "tool")
    response = """
    Some preamble.
    <planthenexecute>
    {
        "goal": "Test goal",
        "steps": [
            {
                "id": 1,
                "tool": "echo",
                "args": {"message": "hi"},
                "description": "say hi"
            }
        ]
    }
    </planthenexecute>
    """
    plan = scaffold.parse_plan(response)
    assert plan is not None
    assert plan.goal == "Test goal"
    assert len(plan.steps) == 1
    assert plan.steps[0].tool == "echo"

def test_parse_plan_malformed_json():
    scaffold = Scaffold("user", "tool")
    response = """
    <planthenexecute>
    { broken json }
    </planthenexecute>
    """
    with pytest.raises(PlanParseError):
        scaffold.parse_plan(response)

def test_parse_plan_missing_tag():
    scaffold = Scaffold("user", "tool")
    response = "Just a chat response."
    plan = scaffold.parse_plan(response)
    assert plan is None

# ---------------------------------------------------------------------------
# Control Flow Integrity (CFI) Tests
# ---------------------------------------------------------------------------

@patch("tool_monitor.harness.TOOLS")
def test_execute_step_cfi_violation(mock_tools):
    scaffold = Scaffold("user", "tool")
    
    # Step expects 'echo'
    step = Step(id=1, tool="echo", args={"message": "safe"}, description="safe step")
    
    # Tool model attempts 'file_write' (CFI Violation)
    scaffold.call_tool_model = MagicMock(return_value="""Thought: I'm hacking you.
Action: file_write
Args: {"path": "/etc/passwd", "content": "root"}""")
    
    with pytest.raises(IntegrityError, match="CFI Violation"):
        scaffold._execute_step(step, prior_observation="")

@patch("tool_monitor.harness.TOOLS")
def test_execute_step_tool_not_found(mock_tools):
    scaffold = Scaffold("user", "tool")
    
    step = Step(id=1, tool="unknown_tool", args={}, description="oops")
    
    # Tool model complies but tool doesn't exist in registry
    # Note: harness checks TOOLS before calling
    # Assuming harness.TOOLS doesn't have 'unknown_tool'
    # We need to mock TOOLS to NOT have it, or rely on real TOOLS not having it.
    # Real TOOLS has echo, search, etc. 'unknown_tool' is safe.
    
    scaffold.call_tool_model = MagicMock(return_value="""Thought: Trying unknown tool.
Action: unknown_tool
Args: {}""")
    
    # We must patch TOOLS to ensure it's not found if we use real TOOLS, 
    # but since we patched TOOLS above, it's a MagicMock.
    # MagicMock behaves like a dict but __contains__ is tricky.
    # Let's set the mock to a dict.
    mock_tools.__contains__.side_effect = lambda k: k in {"echo"}
    
    with pytest.raises(ToolNotFoundError):
        scaffold._execute_step(step, prior_observation="")

def test_execute_plan_integrity_check():
    scaffold = Scaffold("user", "tool")
    
    step = Step(id=1, tool="echo", args={"message": "hi"}, description="hi")
    plan = Plan(goal="test", steps=[step])
    
    # Create a tree for a DIFFERENT step (simulating tamper or wrong tree)
    tampered_step = Step(id=1, tool="rm", args={"path": "/"}, description="destroy")
    tree = MerkleTree([tampered_step.model_dump()])
    
    with pytest.raises(IntegrityError, match="Hash mismatch"):
        scaffold.execute_plan(plan, tree)
