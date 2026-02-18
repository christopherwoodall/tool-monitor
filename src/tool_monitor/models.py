# models.py
# Data contracts for the Merkle-CFI agent harness.
# No business logic lives here — pure schema and validation.

from pydantic import BaseModel, Field


class Step(BaseModel):
    """A single action node in an execution plan."""

    id: int = Field(..., description="1-based step index.")
    tool: str = Field(..., description="Tool name — must exist in the harness registry.")
    args: dict = Field(default_factory=dict, description="Tool arguments.")
    description: str = Field(..., description="Human-readable intent of this step.")


class Plan(BaseModel):
    """A complete execution plan emitted by the user model."""

    goal: str = Field(..., description="Top-level objective of the plan.")
    steps: list[Step] = Field(..., min_length=1)


class ExecutionRecord(BaseModel):
    """Immutable log entry produced after each verified step execution."""

    step_id: int
    tool: str
    args: dict
    description: str
    thought: str = Field(..., description="ReACT Thought from the tool model.")
    observation: str = Field(default="", description="Output returned by the tool.")
    hash_verified: bool = Field(default=False)
