# src/calculator/nexus.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd


# ────────────────────────────────────────────────────────────────────
# Result container
# ────────────────────────────────────────────────────────────────────
@dataclass
class NexusBreachResult:
    """Result of nexus breach calculation for one state."""
    state: str
    has_nexus: bool
    breach_date: Optional[datetime] = None
    breach_type: Optional[str] = None      # 'sales' or 'transactions'
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


# ────────────────────────────────────────────────────────────────────
# Calculator
# ────────────────────────────────────────────────────────────────────
class NexusCalculator:
    """
    Sprint-1 calculator: implements `rolling_12m` and `calendar_prev_curr`
    (other look-back rules can be added later).
    """

    def __init__(self, config: Dict[str, Dict]):
        self.config = config

    # ----------------------------------------------------------------
    # Public entry points
    # ----------------------------------------------------------------
    def analyze_state(self, state: str, sales_data: pd.DataFrame) -> NexusBreachResult:
        """Analyze nexus for a single state."""
        if state not in self.config:
            return NexusBreachResult(state=state, has_nexus=False)

        state_config = self.config[state]
        state_data = sales_data[sales_data["state"] == state].copy()

        if state_data.empty:
            return NexusBreachResult(state=state, has_nexus=False)

        lookback_rule = state_config.get("lookback_rule")

        if lookback_rule == "rolling_12m":
            return self._calculate_rolling_12m(state, state_data, state_config)
        elif lookback_rule == "calendar_prev_curr":
            return self._calculate_calendar_prev_curr(state, state_data, state_config)

        # Un-implemented rule
        return NexusBreachResult(
            state=state, has_nexus=False, lookback_rule=lookback_rule
        )

    def analyze_all_states(self, sales_data: pd.DataFrame) -> List[NexusBreachResult]:
        """
        Run analysis for **every** state referenced in `self.config`.

        • If the state has data, run the appropriate look-back calculation.  
        • If the state has *no* data, still return a `NexusBreachResult`
          (handy for reporting “no nexus” rows).
        • Results are sorted: nexus states first, then alphabetical.
        """
        results: List[NexusBreachResult] = []
        states_in_data = sales_data["state"].unique()

        for state, cfg in self.config.items():
            if state in states_in_data:
                result = self.analyze_state(state, sales_data)
            else:
                result = NexusBreachResult(
                    state=state,
                    has_nexus=False,
                    lookback_rule=cfg.get("lookback_rule"),
                )
            results.append(result)

        # Nexus states first, then A-Z
        return sorted(results, key=lambda r: (not r.has_nexus, r.state))

    # ----------------------------------------------------------------
    # Rolling-12-month rule  (already matched to tests)
    # ----------------------------------------------------------------
    def _calculate_rolling_12m(
        self, state: str, data: pd.DataFrame, config: Dict
    ) -> NexusBreachResult:
        """Calculate rolling 12-month nexus (first breach date)."""
        data = data.sort_values("date").set_index("date")

        # What counts toward threshold?
        if config.get("marketplace_threshold_inclusion", True):
            threshold_sales = data["nexus_sales"] + data["marketplace_sales"]
        else:
            threshold_sales = data["nexus_sales"]

        rolling_sales = threshold_sales.rolling("365D", min_periods=1).sum()
        rolling_trans = data["transaction_count"].rolling("365D", min_periods=1).sum()

        breach = NexusBreachResult(state=state, has_nexus=False, lookback_rule="rolling_12m")

        # Sales threshold
        if config.get("sales_threshold"):
            mask = rolling_sales >= config["sales_threshold"]
            if mask.any():
                first = mask.idxmax()                # first True
                breach.has_nexus = True
                breach.breach_type = "sales"
                breach.breach_date = first
                breach.breach_amount = float(rolling_sales[first])
                return breach

        # Transaction threshold
        if config.get("transaction_threshold"):
            mask = rolling_trans >= config["transaction_threshold"]
            if mask.any():
                first = mask.idxmax()
                breach.has_nexus = True
                breach.breach_type = "transactions"
                breach.breach_date = first
                breach.breach_amount = float(rolling_trans[first])
                return breach

        return breach

    # ----------------------------------------------------------------
    # Calendar previous / current year rule (unchanged)
    # ----------------------------------------------------------------
    def _calculate_calendar_prev_curr(
        self, state: str, data: pd.DataFrame, config: Dict
    ) -> NexusBreachResult:
        """Calculate nexus based on previous OR current calendar year."""
        annual = data.groupby("year").agg(
            {
                "nexus_sales": "sum",
                "marketplace_sales": "sum",
                "transaction_count": "sum",
            }
        )

        if config.get("marketplace_threshold_inclusion", True):
            annual["threshold_sales"] = annual["nexus_sales"] + annual["marketplace_sales"]
        else:
            annual["threshold_sales"] = annual["nexus_sales"]

        breach = NexusBreachResult(
            state=state, has_nexus=False, lookback_rule="calendar_prev_curr"
        )

        for year in annual.index:
            # Sales threshold
            if (
                config.get("sales_threshold")
                and annual.loc[year, "threshold_sales"] >= config["sales_threshold"]
            ):
                breach.has_nexus = True
                breach.breach_type = "sales"
                breach.breach_date = datetime(year, 1, 1)
                breach.breach_amount = float(annual.loc[year, "threshold_sales"])
                return breach

            # Transaction threshold
            if (
                config.get("transaction_threshold")
                and annual.loc[year, "transaction_count"] >= config["transaction_threshold"]
            ):
                breach.has_nexus = True
                breach.breach_type = "transactions"
                breach.breach_date = datetime(year, 1, 1)
                breach.breach_amount = float(annual.loc[year, "transaction_count"])
                return breach

        return breach
