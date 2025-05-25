# config/schema.py
from pydantic import BaseModel, validator
from typing import Optional, Literal
from datetime import datetime

class StateConfig(BaseModel):
    sales_threshold: Optional[float]
    transaction_threshold: Optional[int]
    lookback_rule: Literal['calendar_prev', 'calendar_prev_curr', 'rolling_12m', 'rolling_4q']
    lookback_details: dict = {}
    marketplace_threshold_inclusion: bool = True
    tax_rate: float
    vda_lookback_cap: Optional[int]
    vda_penalty_waived: Optional[bool]
    vda_interest_rule: Optional[str]
    standard_penalty_rate: float = 0.10
    quirk_flags: dict = {}

    @validator('tax_rate')
    def tax_rate_reasonable(cls, v):
        if not 0 <= v <= 0.15:# No state exceeds 15%
            raise ValueError(f'Tax rate {v} seems incorrect')
        return v

    @validator('sales_threshold')
    def sales_threshold_valid(cls, v):
        if v and v not in [100000, 200000, 250000, 500000]:
# Log warning - unusual threshold
            pass
        return v

class Config(BaseModel):
    states: dict[str, StateConfig]

    @classmethod
    def from_yaml(cls, path: str):
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
# Remove DEFAULT before validation
        states = {k: StateConfig(**v) for k, v in data.items() if k != 'DEFAULT'}
        return cls(states=states)