"""Backend fraud detection package used by the main GigShield risk pipeline.

This package is the import-safe integration layer extracted from the
legacy `Fraud detection/app` subsystem.
"""

from .models import FraudDecision, FraudEvaluation
from .services import evaluate_request_fraud

__all__ = ["FraudDecision", "FraudEvaluation", "evaluate_request_fraud"]
