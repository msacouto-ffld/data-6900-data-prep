"""Stage 7 — Evaluate feature value via model comparison.

Trains a simple model on original features only (baseline), then on
original + engineered features, and reports the performance delta.
This is the external quality control that proves the engineered
features actually add value — not just that the personas approved them.

Uses RandomForestClassifier or RandomForestRegressor depending on
the target column type. 5-fold stratified cross-validation.
"""
from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import cross_val_score, StratifiedKFold, KFold
from sklearn.preprocessing import LabelEncoder

from mistake_log import log_event


def _detect_target(df: pd.DataFrame, feat_columns: List[str]) -> Optional[str]:
    """Heuristic: find the most likely target column.

    Looks for columns NOT in feat_ that have low cardinality relative
    to row count (likely categorical target) or are the last non-feat
    column.
    """
    original_cols = [c for c in df.columns if c not in feat_columns]
    if not original_cols:
        return None

    # Common target column name patterns
    target_patterns = [
        "target", "label", "class", "outcome", "y",
        "nobeyesdad", "survived", "churn", "default",
        "diagnosis", "species", "quality",
    ]
    for col in original_cols:
        if col.lower() in target_patterns:
            return col

    # Fallback: last categorical column with reasonable cardinality
    for col in reversed(original_cols):
        if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == object:
            n_unique = df[col].nunique()
            if 2 <= n_unique <= 20:
                return col

    return None


def _prepare_features(
    df: pd.DataFrame,
    columns: List[str],
) -> np.ndarray:
    """Encode categoricals minimally for model input. Returns numpy array."""
    result = df[columns].copy()
    for col in result.columns:
        if pd.api.types.is_string_dtype(result[col]) or result[col].dtype == object:
            result[col] = LabelEncoder().fit_transform(
                result[col].astype(str)
            )
    # Fill any remaining NaN with 0 for model compatibility
    result = result.fillna(0)
    return result.to_numpy(dtype=float)


def evaluate_features(
    df_engineered: pd.DataFrame,
    original_columns: List[str],
    log_path: str,
    target_column: Optional[str] = None,
    random_seed: int = 42,
) -> Optional[Dict[str, Any]]:
    """Run baseline vs engineered model comparison.

    Parameters
    ----------
    df_engineered : DataFrame
        The full engineered DataFrame (original + feat_ columns).
    original_columns : list
        Column names from the original CSV (before engineering).
    log_path : str
        Path to mistake log for event logging.
    target_column : str, optional
        Name of the target column. Auto-detected if not provided.
    random_seed : int
        Random seed for reproducibility.

    Returns
    -------
    dict with comparison results, or None if comparison could not run.
    """
    feat_columns = [c for c in df_engineered.columns if c.startswith("feat_")]

    if not feat_columns:
        print("📊 Feature value comparison: skipped — no engineered features.")
        return None

    # Detect target
    if not target_column:
        target_column = _detect_target(df_engineered, feat_columns)

    if not target_column:
        print(
            "📊 Feature value comparison: skipped — could not identify "
            "a target column. To enable, specify the target column name."
        )
        log_event(
            log_path, "edge_case_triggered", "evaluate_features",
            "No target column detected for model comparison",
            "Comparison skipped — user can specify target manually",
        )
        return None

    if target_column not in df_engineered.columns:
        print(f"📊 Feature value comparison: skipped — target '{target_column}' not found.")
        return None

    print(f"📊 Evaluating feature value...")
    print(f"   Target column: {target_column}")

    y_raw = df_engineered[target_column]

    # Determine task type
    is_classification = (
        pd.api.types.is_string_dtype(y_raw) or y_raw.dtype == object
        or str(y_raw.dtype) == "string"
        or y_raw.nunique() <= 20
    )

    # Encode target
    if pd.api.types.is_string_dtype(y_raw) or y_raw.dtype == object or str(y_raw.dtype) == "string":
        le = LabelEncoder()
        y = le.fit_transform(y_raw.astype(str))
    else:
        y = y_raw.values

    # Prepare feature sets
    baseline_cols = [c for c in original_columns if c != target_column]
    engineered_cols = baseline_cols + feat_columns

    # Filter to columns that actually exist
    baseline_cols = [c for c in baseline_cols if c in df_engineered.columns]
    engineered_cols = [c for c in engineered_cols if c in df_engineered.columns]

    X_baseline = _prepare_features(df_engineered, baseline_cols)
    X_engineered = _prepare_features(df_engineered, engineered_cols)

    # Model and CV setup
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        if is_classification:
            model_cls = RandomForestClassifier
            model_params = {
                "n_estimators": 100,
                "max_depth": 30,
                "random_state": random_seed,
            }
            scoring_primary = "accuracy"
            scoring_secondary = "f1_weighted"
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_seed)
            task_type = "classification"
        else:
            model_cls = RandomForestRegressor
            model_params = {
                "n_estimators": 100,
                "max_depth": 30,
                "random_state": random_seed,
            }
            scoring_primary = "r2"
            scoring_secondary = "neg_mean_squared_error"
            cv = KFold(n_splits=5, shuffle=True, random_state=random_seed)
            task_type = "regression"

        # Baseline scores
        scores_base_primary = cross_val_score(
            model_cls(**model_params), X_baseline, y,
            cv=cv, scoring=scoring_primary,
        )
        scores_base_secondary = cross_val_score(
            model_cls(**model_params), X_baseline, y,
            cv=cv, scoring=scoring_secondary,
        )

        # Engineered scores
        scores_eng_primary = cross_val_score(
            model_cls(**model_params), X_engineered, y,
            cv=cv, scoring=scoring_primary,
        )
        scores_eng_secondary = cross_val_score(
            model_cls(**model_params), X_engineered, y,
            cv=cv, scoring=scoring_secondary,
        )

    # Build result
    primary_label = scoring_primary.replace("_", " ").title()
    secondary_label = scoring_secondary.replace("neg_", "").replace("_", " ").title()

    delta_primary = scores_eng_primary.mean() - scores_base_primary.mean()
    delta_secondary = scores_eng_secondary.mean() - scores_base_secondary.mean()

    result = {
        "task_type": task_type,
        "target_column": target_column,
        "model": "RandomForestClassifier" if is_classification else "RandomForestRegressor",
        "model_params": {"n_estimators": 100, "max_depth": 30},
        "cv_folds": 5,
        "random_seed": random_seed,
        "baseline_features": len(baseline_cols),
        "engineered_features": len(feat_columns),
        "total_features": len(engineered_cols),
        "metrics": {
            "primary": {
                "name": primary_label,
                "baseline": round(scores_base_primary.mean(), 4),
                "baseline_std": round(scores_base_primary.std(), 4),
                "engineered": round(scores_eng_primary.mean(), 4),
                "engineered_std": round(scores_eng_primary.std(), 4),
                "delta": round(delta_primary, 4),
            },
            "secondary": {
                "name": secondary_label,
                "baseline": round(scores_base_secondary.mean(), 4),
                "baseline_std": round(scores_base_secondary.std(), 4),
                "engineered": round(scores_eng_secondary.mean(), 4),
                "engineered_std": round(scores_eng_secondary.std(), 4),
                "delta": round(delta_secondary, 4),
            },
        },
        "value_added": delta_primary > 0,
    }

    # Console output
    print(f"   Task type: {task_type}")
    print(f"   Model: RandomForest (n_estimators=100, max_depth=30)")
    print(f"   Evaluation: 5-fold cross-validation")
    print()
    print(f"   BASELINE ({len(baseline_cols)} original features)")
    print(f"     {primary_label}: {result['metrics']['primary']['baseline']:.4f} "
          f"(±{result['metrics']['primary']['baseline_std']:.4f})")
    print(f"     {secondary_label}: {result['metrics']['secondary']['baseline']:.4f} "
          f"(±{result['metrics']['secondary']['baseline_std']:.4f})")
    print()
    print(f"   WITH ENGINEERED FEATURES ({len(engineered_cols)} total features)")
    print(f"     {primary_label}: {result['metrics']['primary']['engineered']:.4f} "
          f"(±{result['metrics']['primary']['engineered_std']:.4f})")
    print(f"     {secondary_label}: {result['metrics']['secondary']['engineered']:.4f} "
          f"(±{result['metrics']['secondary']['engineered_std']:.4f})")
    print()
    print(f"   DELTA")
    print(f"     {primary_label}: {delta_primary:+.4f}")
    print(f"     {secondary_label}: {delta_secondary:+.4f}")
    print()

    if result["value_added"]:
        print(f"   ✅ Engineered features improved {primary_label.lower()} by "
              f"{abs(delta_primary):.4f}")
    else:
        print(f"   ⚠️ Engineered features did not improve {primary_label.lower()}")

    # Log the result
    log_event(
        log_path, "edge_case_triggered", "evaluate_features",
        f"Feature value comparison: {primary_label} delta = {delta_primary:+.4f} "
        f"(baseline={result['metrics']['primary']['baseline']:.4f}, "
        f"engineered={result['metrics']['primary']['engineered']:.4f})",
        "Comparison completed — results included in transformation report",
    )

    return result


if __name__ == "__main__":
    # Quick test with a small synthetic dataset
    np.random.seed(42)
    n = 200
    df = pd.DataFrame({
        "age": np.random.randint(18, 65, n),
        "income": np.random.normal(50000, 15000, n),
        "category": np.random.choice(["A", "B", "C"], n),
        "target": np.random.choice(["yes", "no"], n),
    })
    # Add some engineered features
    df["feat_age_scaled"] = (df["age"] - df["age"].min()) / (df["age"].max() - df["age"].min())
    df["feat_income_scaled"] = (df["income"] - df["income"].min()) / (df["income"].max() - df["income"].min())

    import tempfile, os
    from mistake_log import init_mistake_log
    log = os.path.join(tempfile.gettempdir(), "test-eval.md")
    init_mistake_log(log, "test")

    result = evaluate_features(
        df,
        original_columns=["age", "income", "category", "target"],
        log_path=log,
    )
    if result:
        print(f"\nValue added: {result['value_added']}")
    os.remove(log)
