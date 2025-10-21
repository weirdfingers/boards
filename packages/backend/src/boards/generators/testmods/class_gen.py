"""Test helper generator class for loader unit tests (class-based)."""

from pydantic import BaseModel

from ..base import BaseGenerator


class _Input(BaseModel):
    text: str = "hello"


class _Output(BaseModel):
    text: str


class ClassGen(BaseGenerator):
    name = "class-gen"
    artifact_type = "text"
    description = "Test class-based generator"

    def __init__(self, suffix: str | None = None):
        self.suffix = suffix or "!"

    def get_input_schema(self) -> type[_Input]:
        return _Input

    def get_output_schema(self) -> type[_Output]:
        return _Output

    async def generate(self, inputs: _Input, context) -> _Output:  # type: ignore[override]
        return _Output(text=f"{inputs.text}{self.suffix}")

    async def estimate_cost(self, inputs: _Input) -> float:  # type: ignore[override]
        return 0.0
