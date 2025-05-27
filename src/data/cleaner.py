# Data hygiene module
import pandas as pd
import numpy as np
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class DataCleaner:
    """Handles all data validation and cleaning"""
    
    REQUIRED_COLUMNS = ['date', 'state', 'gross_sales']
    OPTIONAL_COLUMNS = ['transaction_count', 'marketplace_sales']
    
    @staticmethod
    def clean(df: pd.DataFrame) -> pd.DataFrame:
        """Main cleaning function with SALT-specific logic"""
        
        # 1. Validate required columns
        missing = set(DataCleaner.REQUIRED_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        # 2. Create a copy to avoid modifying original
        clean_df = df.copy()
        
        # 3. Date handling
        clean_df['date'] = pd.to_datetime(clean_df['date'], errors='coerce')
        invalid_dates = clean_df['date'].isna().sum()
        if invalid_dates > 0:
            logger.warning(f"Dropping {invalid_dates} rows with invalid dates")
            clean_df = clean_df.dropna(subset=['date'])
        
        # 4. Sales data cleaning
        clean_df['gross_sales'] = pd.to_numeric(clean_df['gross_sales'], errors='coerce').fillna(0)
        
        # SALT-specific: Some states don't count negative sales toward nexus
        clean_df['nexus_sales'] = clean_df['gross_sales'].clip(lower=0)
        
        # 5. Optional columns with defaults
        if 'transaction_count' in clean_df.columns:
            clean_df['transaction_count'] = pd.to_numeric(
                clean_df['transaction_count'], errors='coerce'
            ).fillna(0).astype('Int64')
        else:
            clean_df['transaction_count'] = 0
            
        if 'marketplace_sales' in clean_df.columns:
            clean_df['marketplace_sales'] = pd.to_numeric(
                clean_df['marketplace_sales'], errors='coerce'
            ).fillna(0)
        else:
            clean_df['marketplace_sales'] = 0
        
        # 6. State code standardization
        clean_df['state'] = clean_df['state'].str.upper().str.strip()
        
        # 7. Remove duplicates (sum sales for same state/date)
        if clean_df.duplicated(subset=['date', 'state']).any():
            logger.warning("Found duplicate state/date entries, aggregating...")
            clean_df = clean_df.groupby(['date', 'state'], as_index=False).agg({
                'gross_sales': 'sum',
                'nexus_sales': 'sum',
                'transaction_count': 'sum',
                'marketplace_sales': 'sum'
            })
        
        # 8. Sort for efficiency
        clean_df = clean_df.sort_values(['state', 'date'])
        
        # 9. Add helper columns
        clean_df['year'] = clean_df['date'].dt.year
        clean_df['month'] = clean_df['date'].dt.to_period('M')
        
        return clean_df