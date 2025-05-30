# src/calculator/nexus.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd


# ─────────────────────────────────────────────────────────────
# Result container
# ─────────────────────────────────────────────────────────────
@dataclass
class NexusBreachResult:
    state: str
    has_nexus: bool
    breach_date: Optional[datetime] = None
    breach_type: Optional[str] = None     # 'sales' | 'transactions'
    breach_amount: Optional[float] = None
    lookback_rule: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "has_nexus": self.has_nexus,
            "breach_date": self.breach_date.strftime("%Y-%m-%d") if self.breach_date else None,
            "breach_type": self.breach_type,
            "breach_amount": round(self.breach_amount, 2) if self.breach_amount else None,
            "lookback_rule": self.lookback_rule,
        }


# ─────────────────────────────────────────────────────────────
# Calculator
# ─────────────────────────────────────────────────────────────
class NexusCalculator:
    """
    Implements `rolling_12m` and `calendar_prev_curr` look-back rules.
    Accepts either dict configs *or* Pydantic StateConfig models.
    """

    def __init__(self, config: Dict[str, Dict]):
        self.config = config

    # ---------- utilities ------------------------------------
    @staticmethod
    def _cfg_to_dict(cfg) -> Dict:
        """Pydantic model → dict; if already dict, return as-is."""
        return cfg.model_dump() if hasattr(cfg, "model_dump") else dict(cfg)

    # ---------- public api -----------------------------------
    def analyze_state(self, state: str, sales_data: pd.DataFrame) -> NexusBreachResult:
        if state not in self.config:
            return NexusBreachResult(state=state, has_nexus=False)

        cfg = self._cfg_to_dict(self.config[state])
        state_data = sales_data[sales_data["state"] == state]

        if state_data.empty:
            return NexusBreachResult(state=state, has_nexus=False)

        lookback_rule = cfg.get("lookback_rule")

        if lookback_rule == "rolling_12m":
            return self._calculate_rolling_12m(state, state_data, cfg)
        if lookback_rule == "calendar_prev_curr":
            return self._calculate_calendar_prev_curr(state, state_data, cfg)

        return NexusBreachResult(state=state, has_nexus=False, lookback_rule=lookback_rule)

    def analyze_all_states(self, sales_data: pd.DataFrame) -> List[NexusBreachResult]:
        results: List[NexusBreachResult] = []
        states_in_data = sales_data["state"].unique()

        for state, cfg_model in self.config.items():
            cfg = self._cfg_to_dict(cfg_model)

            if state in states_in_data:
                res = self.analyze_state(state, sales_data)
            else:
                res = NexusBreachResult(
                    state=state,
                    has_nexus=False,
                    lookback_rule=cfg.get("lookback_rule"),
                )
            results.append(res)

        return sorted(results, key=lambda r: (not r.has_nexus, r.state))

    # ---------- rule: rolling-12-month -----------------------
    def _calculate_rolling_12m(
        self, state: str, data: pd.DataFrame, cfg: Dict
    ) -> NexusBreachResult:
        data = data.sort_values("date").set_index("date")

        if cfg.get("marketplace_threshold_inclusion", True):
            threshold_sales = data["nexus_sales"] + data["marketplace_sales"]
        else:
            threshold_sales = data["nexus_sales"]

        rolling_sales = threshold_sales.rolling("365D", min_periods=1).sum()
        rolling_trans = data["transaction_count"].rolling("365D", min_periods=1).sum()

        res = NexusBreachResult(state=state, has_nexus=False, lookback_rule="rolling_12m")

        if cfg.get("sales_threshold"):
            mask = rolling_sales >= cfg["sales_threshold"]
            if mask.any():
                first = mask.idxmax()
                res.has_nexus = True
                res.breach_type = "sales"
                res.breach_date = first
                res.breach_amount = float(rolling_sales[first])
                return res

        if cfg.get("transaction_threshold"):
            mask = rolling_trans >= cfg["transaction_threshold"]
            if mask.any():
                first = mask.idxmax()
                res.has_nexus = True
                res.breach_type = "transactions"
                res.breach_date = first
                res.breach_amount = float(rolling_trans[first])

        return res

    # ---------- rule: calendar prev / curr -------------------
    def _calculate_calendar_prev_curr(
        self, state: str, data: pd.DataFrame, cfg: Dict
    ) -> NexusBreachResult:
        annual = data.groupby("year").agg(
            {
                "nexus_sales": "sum",
                "marketplace_sales": "sum",
                "transaction_count": "sum",
            }
        )

        if cfg.get("marketplace_threshold_inclusion", True):
            annual["threshold_sales"] = annual["nexus_sales"] + annual["marketplace_sales"]
        else:
            annual["threshold_sales"] = annual["nexus_sales"]

        res = NexusBreachResult(state=state, has_nexus=False, lookback_rule="calendar_prev_curr")

        for year in annual.index:
            if cfg.get("sales_threshold") and annual.loc[year, "threshold_sales"] >= cfg["sales_threshold"]:
                res.has_nexus = True
                res.breach_type = "sales"
                res.breach_date = datetime(year, 1, 1)
                res.breach_amount = float(annual.loc[year, "threshold_sales"])
                return res

            if cfg.get("transaction_threshold") and annual.loc[year, "transaction_count"] >= cfg["transaction_threshold"]:
                res.has_nexus = True
                res.breach_type = "transactions"
                res.breach_date = datetime(year, 1, 1)
                res.breach_amount = float(annual.loc[year, "transaction_count"])
                return res

        return res
