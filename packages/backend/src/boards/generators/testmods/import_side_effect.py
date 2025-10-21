"""Test helper module that registers on import (import-based)."""

from pydantic import BaseModel

from ..base import BaseGenerator
from ..registry import registry


class _Input(BaseModel):
    pass


class _Output(BaseModel):
    pass


class ImportGen(BaseGenerator):
    name = "import-gen"
    artifact_type = "text"
    description = "Test import-based generator"

    def get_input_schema(self) -> type[_Input]:
        return _Input

    def get_output_schema(self) -> type[_Output]:
        return _Output

    async def generate(self, inputs: _Input, context) -> _Output:  # type: ignore[override]
        return _Output()

    async def estimate_cost(self, inputs: _Input) -> float:  # type: ignore[override]
        return 0.0


registry.register(ImportGen())
