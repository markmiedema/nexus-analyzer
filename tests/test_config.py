# tests/test_config.py
# tests/test_config.py
"""
Basic sanity checks for src/config/state_config.yaml
Run:  pytest -q tests/test_config.py
"""

import pathlib
import yaml
import pytest
from src.config.schema import NexusConfig

# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

CONFIG_PATH = pathlib.Path("src/config/state_config.yaml")
REQUIRED_FIELDS = {"lookback_rule", "sales_threshold", "transaction_threshold"}
ALLOWED_LOOKBACK = {"rolling_12m", "calendar_prev_curr"}  # extend as added

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _load_yaml():
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------


def test_yaml_loads_without_error():
    """YAML parses and produces a dict with at least one state."""
    data = _load_yaml()
    assert isinstance(data, dict) and data, "YAML empty or not a mapping"


@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_each_state_has_required_fields(field):
    """Every state entry contains the required keys (may be null)."""
    data = _load_yaml()
    for state, cfg in data.items():
        assert field in cfg, f"{state} missing '{field}' key"


def test_lookback_rule_values_valid():
    """Look-back rules limited to allowed set."""
    cfg = NexusConfig.from_yaml(CONFIG_PATH)
    for state, params in cfg.states.items():
        assert (
            params.lookback_rule in ALLOWED_LOOKBACK
        ), f"{state} invalid lookback_rule '{params.lookback_rule}'"
