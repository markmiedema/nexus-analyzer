# src/data/cleaner.py
import logging
from typing import Dict, List

import pandas as pd

logger = logging.getLogger(__name__)


class DataCleaner:
    """Validate and clean raw sales data for SALT-nexus analysis."""

    REQUIRED_COLUMNS: List[str] = ["date", "state", "gross_sales"]
    OPTIONAL_COLUMNS: List[str] = ["transaction_count", "marketplace_sales"]

    # ── public api ──────────────────────────────────────────────
    @staticmethod
    def clean(df: pd.DataFrame) -> pd.DataFrame:
        # 1. mandatory columns
        missing = set(DataCleaner.REQUIRED_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        clean_df = df.copy()

        # 2. dates  (keep bad dates as NaT; tests expect TX row preserved)
        clean_df["date"] = pd.to_datetime(clean_df["date"], errors="coerce")
        bad_dates = clean_df["date"].isna().sum()
        if bad_dates:
            logger.warning(f"{bad_dates} rows contain invalid dates (kept as NaT)")

        # 3. numerics
        clean_df["gross_sales"] = pd.to_numeric(
            clean_df["gross_sales"], errors="coerce"
        ).fillna(0)
        clean_df["nexus_sales"] = clean_df["gross_sales"].clip(lower=0)

        clean_df["transaction_count"] = (
            pd.to_numeric(clean_df.get("transaction_count", 0), errors="coerce")
            .fillna(0)
            .round()                # 2.5  → 2   (safe for Int64 cast)
            .astype("Int64")
        )

        if "marketplace_sales" not in clean_df.columns:
            clean_df["marketplace_sales"] = 0
        clean_df["marketplace_sales"] = (
            pd.to_numeric(clean_df["marketplace_sales"], errors="coerce").fillna(0)
        )

        # 4. state codes
        clean_df["state"] = clean_df["state"].astype(str).str.upper().str.strip()

        # 5. aggregate ALL rows per state (earliest date kept)
        clean_df = DataCleaner._aggregate_by_state(clean_df)

        # 6. helper columns & ordering
        clean_df = clean_df.sort_values("state").reset_index(drop=True)
        clean_df["year"] = clean_df["date"].dt.year
        clean_df["month"] = clean_df["date"].dt.to_period("M")

        return clean_df

    # ── helpers ─────────────────────────────────────────────────
    @staticmethod
    def _aggregate_by_state(df: pd.DataFrame) -> pd.DataFrame:
        """Collapse multiple rows per state into one."""
        if df.duplicated(subset=["state"]).any():
            logger.warning("Aggregating duplicate state rows.")
            df = (
                df.groupby("state", as_index=False)
                .agg(
                    {
                        "date": "min",           # keep earliest date
                        "gross_sales": "sum",
                        "nexus_sales": "sum",
                        "transaction_count": "sum",
                        "marketplace_sales": "sum",
                    }
                )
            )
        return df

    # ── analytics helpers ──────────────────────────────────────
    @staticmethod
    def validate_data_quality(df: pd.DataFrame) -> Dict:
        report = {
            "total_rows": len(df),
            "date_range": {"start": df["date"].min(), "end": df["date"].max()},
            "states_found": sorted(df["state"].unique().tolist()),
            "missing_values": df.isnull().sum().to_dict(),
            "negative_sales_rows": int((df["gross_sales"] < 0).sum()),
            "data_quality_score": 100.0,
        }
        if report["missing_values"].get("date", 0):
            report["data_quality_score"] -= 20
        if report["negative_sales_rows"] > len(df) * 0.10:
            report["data_quality_score"] -= 10
        return report

    @staticmethod
    def prepare_summary_stats(df: pd.DataFrame) -> pd.DataFrame:
        return (
            df.groupby("state")
            .agg(
                {
                    "gross_sales": ["sum", "count", "min", "max"],
                    "nexus_sales": "sum",
                    "transaction_count": "sum",
                    "marketplace_sales": "sum",
                    "date": ["min", "max"],
                }
            )
            .round(2)
        )
