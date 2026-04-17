from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FraudDecision(str, Enum):
    CLEAN = "Clean"
    REVIEW = "Review"
    SUSPICIOUS = "Suspicious"
    BLOCK = "Block"


@dataclass
class FraudEvaluation:
    score: float
    flag: FraudDecision
    signals: dict[str, float] = field(default_factory=dict)
    requires_manual_review: bool = False
