import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("numpy")
pytest.importorskip("sklearn")

from src.data_generator import generate_conflict_events, generate_news_signals, generate_social_signals
from src.model_pipeline import build_monthly_features, train_model


def test_pipeline_end_to_end():
    conflict_df = generate_conflict_events(months=10)
    news_df = generate_news_signals(conflict_df)
    social_df = generate_social_signals(news_df)
    features = build_monthly_features(conflict_df, news_df, social_df)

    assert not features.empty
    assert {"protest_count", "military_events", "conflict_escalation"}.issubset(features.columns)

    _, scored, metrics = train_model(features)
    assert "risk_score" in scored.columns
    assert 0.0 <= metrics["roc_auc"] <= 1.0
