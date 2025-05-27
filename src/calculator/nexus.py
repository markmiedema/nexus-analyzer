# Core calculation logic
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass

@dataclass
class NexusBreachResult:
    """Result of nexus breach calculation for one state"""
    state: str
    has_nexus: bool
    breach_date: Optional[datetime] = None
    breach_type: Optional[str] = None  # 'sales' or 'transactions'
    breach_amount: Optional[float] = None
    lookback_rule: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'state': self.state,
            'has_nexus': self.has_nexus,
            'breach_date': self.breach_date.strftime('%Y-%m-%d') if self.breach_date else None,
            'breach_type': self.breach_type,
            'breach_amount': round(self.breach_amount, 2) if self.breach_amount else None,
            'lookback_rule': self.lookback_rule
        }

class NexusCalculator:
    """Sprint 1: Implements rolling_12m and calendar_prev_curr only"""
    
    def __init__(self, config: dict):
        self.config = config
    
    def analyze_state(self, state: str, sales_data: pd.DataFrame) -> NexusBreachResult:
        """Analyze nexus for a single state"""
        if state not in self.config:
            return NexusBreachResult(state=state, has_nexus=False)
            
        state_config = self.config[state]
        state_data = sales_data[sales_data['state'] == state].copy()
        
        if state_data.empty:
            return NexusBreachResult(state=state, has_nexus=False)
        
        # Route to appropriate calculation method
        lookback_rule = state_config.get('lookback_rule')
        
        if lookback_rule == 'rolling_12m':
            return self._calculate_rolling_12m(state, state_data, state_config)
        elif lookback_rule == 'calendar_prev_curr':
            return self._calculate_calendar_prev_curr(state, state_data, state_config)
        else:
            # Not implemented in Sprint 1
            return NexusBreachResult(
                state=state, 
                has_nexus=False,
                lookback_rule=lookback_rule
            )
    
    def _calculate_rolling_12m(self, state: str, data: pd.DataFrame, 
                              config: dict) -> NexusBreachResult:
        """Calculate rolling 12-month nexus"""
        data = data.sort_values('date').set_index('date')
        
        # Calculate what counts toward threshold
        if config.get('marketplace_threshold_inclusion', True):
            threshold_sales = data['nexus_sales'] + data['marketplace_sales']
        else:
            threshold_sales = data['nexus_sales']
        
        # Rolling 365-day window
        rolling_sales = threshold_sales.rolling('365D', min_periods=1).sum()
        rolling_trans = data['transaction_count'].rolling('365D', min_periods=1).sum()
        
        # Check sales threshold
        breach_result = NexusBreachResult(state=state, has_nexus=False, lookback_rule='rolling_12m')
        
        if config.get('sales_threshold'):
            sales_breach = rolling_sales >= config['sales_threshold']
            if sales_breach.any():
                breach_idx = sales_breach.idxmax()
                breach_result.has_nexus = True
                breach_result.breach_date = breach_idx
                breach_result.breach_type = 'sales'
                breach_result.breach_amount = float(rolling_sales[breach_idx])
                return breach_result
        
        # Check transaction threshold
        if config.get('transaction_threshold'):
            trans_breach = rolling_trans >= config['transaction_threshold']
            if trans_breach.any():
                breach_idx = trans_breach.idxmax()
                breach_result.has_nexus = True
                breach_result.breach_date = breach_idx
                breach_result.breach_type = 'transactions'
                breach_result.breach_amount = float(rolling_trans[breach_idx])
                return breach_result
        
        return breach_result
    
    def _calculate_calendar_prev_curr(self, state: str, data: pd.DataFrame,
                                     config: dict) -> NexusBreachResult:
        """Calculate based on previous OR current calendar year"""
        # Annual aggregation
        annual_summary = data.groupby('year').agg({
            'nexus_sales': 'sum',
            'marketplace_sales': 'sum',
            'transaction_count': 'sum'
        })
        
        if config.get('marketplace_threshold_inclusion', True):
            annual_summary['threshold_sales'] = (
                annual_summary['nexus_sales'] + annual_summary['marketplace_sales']
            )
        else:
            annual_summary['threshold_sales'] = annual_summary['nexus_sales']
        
        breach_result = NexusBreachResult(state=state, has_nexus=False, lookback_rule='calendar_prev_curr')
        
        # Check each year
        for year in annual_summary.index:
            # Sales threshold
            if (config.get('sales_threshold') and 
                annual_summary.loc[year, 'threshold_sales'] >= config['sales_threshold']):
                breach_result.has_nexus = True
                breach_result.breach_date = datetime(year, 1, 1)  # Nexus starts Jan 1
                breach_result.breach_type = 'sales'
                breach_result.breach_amount = float(annual_summary.loc[year, 'threshold_sales'])
                return breach_result
            
            # Transaction threshold
            if (config.get('transaction_threshold') and
                annual_summary.loc[year, 'transaction_count'] >= config['transaction_threshold']):
                breach_result.has_nexus = True
                breach_result.breach_date = datetime(year, 1, 1)
                breach_result.breach_type = 'transactions'
                breach_result.breach_amount = float(annual_summary.loc[year, 'transaction_count'])
                return breach_result
        
        return breach_result