"""ReadResult — platform-neutral shape returned by a READ.

The actual pattern-extraction code is in each adapter (e.g.,
`sgcl/adapters/windows_uia/_readers.py` for UIA). They all return this
same shape.

`supported=False` is honest — the adapter could not extract a value.
Callers should not infer "the control had an empty value" from a
`False`; that's a different statement (and would surface as `value=""`
with `supported=True`, source="label").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReadResult:
    supported: bool
    source: str
    value: str | None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "supported": self.supported,
            "source": self.source,
            "value": self.value,
            "details": dict(self.details),
        }
