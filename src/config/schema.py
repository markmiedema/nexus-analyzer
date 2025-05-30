# src/config/schema.py
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal, Dict, List
from datetime import datetime
from enum import Enum

class LookbackRule(str, Enum):
    """Lookback rules supported in MVP"""
    ROLLING_12M = "rolling_12m"
    CALENDAR_PREV_CURR = "calendar_prev_curr"
    # Future additions:
    # CALENDAR_PREV = "calendar_prev"
    # ROLLING_4Q = "rolling_4q"
    # ACCOUNTING_YEAR = "accounting_year"

class StateConfig(BaseModel):
    """Configuration for a single state's nexus rules"""
    
    # Thresholds
    sales_threshold: Optional[float] = Field(None, ge=0, le=10_000_000)
    transaction_threshold: Optional[int] = Field(None, ge=0, le=10_000)
    
    # Lookback configuration
    lookback_rule: LookbackRule
    lookback_details: Dict = Field(default_factory=dict)
    
    # Marketplace facilitator
    marketplace_threshold_inclusion: bool = True
    
    # Tax information
    tax_rate: float = Field(..., ge=0, le=0.15)
    
    # VDA (Voluntary Disclosure Agreement) settings
    vda_lookback_cap: Optional[int] = Field(None, ge=0, le=20)  # quarters
    vda_penalty_waived: Optional[bool] = None
    vda_interest_rule: Optional[str] = None
    
    # Penalties and interest
    standard_penalty_rate: float = Field(0.10, ge=0, le=0.50)
    interest_rate: float = Field(0.06, ge=0, le=0.12)  # Annual rate
    
    # State-specific quirks
    quirk_flags: Dict = Field(default_factory=dict)
    
    # Metadata
    effective_date: Optional[str] = None  # When these rules took effect
    notes: Optional[str] = None
    
    @validator('sales_threshold', 'transaction_threshold')
    def at_least_one_threshold(cls, v, values):
        """Ensure state has at least one threshold defined"""
        if v is None and values.get('sales_threshold') is None:
            raise ValueError("State must have at least one threshold (sales or transaction)")
        return v
    
    @validator('tax_rate')
    def tax_rate_reasonable(cls, v):
        """Validate tax rate is within reasonable bounds"""
        if not 0 <= v <= 0.15:  # No state exceeds 15%
            raise ValueError(f'Tax rate {v} seems incorrect (should be 0-15%)')
        return v
    
    @validator('sales_threshold')
    def sales_threshold_common_values(cls, v):
        """Warn about unusual thresholds"""
        common_thresholds = [100000, 200000, 250000, 500000, 1000000]
        if v and v not in common_thresholds:
            # Just log a warning, don't fail
            print(f"Warning: Unusual sales threshold ${v:,}")
        return v
    
    @property
    def has_transaction_threshold(self) -> bool:
        """Check if state uses transaction count threshold"""
        return self.transaction_threshold is not None
    
    @property
    def has_sales_threshold(self) -> bool:
        """Check if state uses sales threshold"""
        return self.sales_threshold is not None
    
    def format_thresholds(self) -> str:
        """Human-readable threshold description"""
        parts = []
        if self.sales_threshold:
            parts.append(f"${self.sales_threshold:,.0f} in sales")
        if self.transaction_threshold:
            parts.append(f"{self.transaction_threshold:,} transactions")
        return " OR ".join(parts) if parts else "No thresholds defined"

class NexusConfig(BaseModel):
    """Full nexus configuration for all states"""
    states: Dict[str, StateConfig]
    metadata: Dict = Field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, path: str) -> "NexusConfig":
        """Load configuration from YAML file"""
        import yaml
        from pathlib import Path
        
        yaml_path = Path(path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        
        # Remove DEFAULT and other special keys
        states = {}
        metadata = {}
        skipped = []
        
        for key, value in data.items():
            if key in ['DEFAULT', '_metadata', 'metadata']:
                metadata[key] = value
                continue
            
            try:
                # Only include states with implemented lookback rules for MVP
                lookback = value.get('lookback_rule')
                if lookback in ['rolling_12m', 'calendar_prev_curr']:
                    states[key] = StateConfig(**value)
                else:
                    skipped.append((key, lookback))
            except Exception as e:
                print(f"Warning: Skipping {key} - {e}")
                skipped.append((key, str(e)))
        
        if skipped:
            print(f"\nMVP: Processing {len(states)} states")
            print(f"Skipped {len(skipped)} states with unimplemented features:")
            for state, reason in skipped[:5]:  # Show first 5
                print(f"  - {state}: {reason}")
            if len(skipped) > 5:
                print(f"  ... and {len(skipped) - 5} more")
        
        return cls(states=states, metadata=metadata)
    
    def get_state_config(self, state: str) -> Optional[StateConfig]:
        """Get configuration for a specific state"""
        return self.states.get(state.upper())
    
    def list_states(self) -> List[str]:
        """Get list of configured states"""
        return sorted(self.states.keys())
    
    def summary_report(self) -> Dict:
        """Generate summary statistics about configurations"""
        return {
            'total_states': len(self.states),
            'states_with_sales_threshold': sum(
                1 for s in self.states.values() if s.has_sales_threshold
            ),
            'states_with_transaction_threshold': sum(
                1 for s in self.states.values() if s.has_transaction_threshold
            ),
            'states_by_lookback_rule': {
                rule: sum(1 for s in self.states.values() if s.lookback_rule == rule)
                for rule in LookbackRule
            },
            'marketplace_inclusion_states': sum(
                1 for s in self.states.values() if s.marketplace_threshold_inclusion
            )
        }

# Validation helper functions
def validate_state_code(state: str) -> str:
    """Validate and standardize state code"""
    state = state.upper().strip()
    
    valid_states = {
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
        'DC', 'PR'  # DC and Puerto Rico
    }
    
    if state not in valid_states:
        raise ValueError(f"Invalid state code: {state}")
    
    return state

# Example usage and testing
if __name__ == "__main__":
    # Test creating a state config
    ca_config = StateConfig(
        sales_threshold=500000,
        transaction_threshold=None,
        lookback_rule=LookbackRule.ROLLING_12M,
        marketplace_threshold_inclusion=False,
        tax_rate=0.0725,
        vda_lookback_cap=8,
        standard_penalty_rate=0.10
    )
    
    print(f"CA Thresholds: {ca_config.format_thresholds()}")
    
    # Test loading from YAML
    try:
        config = NexusConfig.from_yaml('src/config/state_config.yaml')
        print(f"\nLoaded {len(config.states)} states")
        
        # Show summary
        summary = config.summary_report()
        print("\nConfiguration Summary:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
            
    except FileNotFoundError:
        print("Config file not found - create src/config/state_config.yaml first")