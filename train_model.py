"""Standalone training entrypoint for the GigShield v3 risk model.

Run:
    python train_model.py

Trains and persists:
- saved_model/risk_model.pkl
- saved_model/model_meta.json
- saved_model/feature_importance.csv
"""

from model import FEATURE_IMPORTANCE_PATH, META_PATH, MODEL_PATH, manager


if __name__ == "__main__":
    samples, r2, rmse = manager.train_and_save(n_samples=8000)
    meta = manager.get_meta()

    print(f"\n{'═' * 60}")
    print("  GigShield Risk Model v3 — Training Complete")
    print(f"{'═' * 60}")
    print(f"  Samples               : {samples}")
    print(f"  R² (test)             : {r2:.4f}")
    print(f"  RMSE (test)           : {rmse:.4f}")
    print(f"  Linear baseline R²    : {meta.get('linear_baseline_r2', 0):.4f}")
    print(f"  Nonlinearity gap      : {meta.get('nonlinearity_gap', 0):.4f}")
    print(f"  Model artifact        : {MODEL_PATH}")
    print(f"  Metadata artifact     : {META_PATH}")
    print(f"  Feature importance CSV: {FEATURE_IMPORTANCE_PATH}")

    importances = meta.get("feature_importances", {})
    if importances:
        print("\n  ── Top Feature Importances ──")
        for feat, imp in sorted(importances.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"    {feat:28s} {imp:.4f}")

    print(f"\n{'═' * 60}\n")
