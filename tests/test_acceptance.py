import pytest
import pandas as pd
from pathlib import Path
import tempfile
from datetime import datetime, timedelta

from src.config.schema import NexusConfig
from src.data.cleaner import DataCleaner
from src.calculator.nexus import NexusCalculator
from src.export.excel import ExcelExporter

def test_end_to_end_acceptance():
    """Complete workflow test with realistic data"""
    
    # 1. Create test data that should trigger nexus
    test_data = []
    base_date = datetime(2022, 1, 1)
    
    # California - should breach rolling 12m at $500k
    for i in range(365):
        test_data.append({
            'date': base_date + timedelta(days=i),
            'state': 'CA',
            'gross_sales': 1500,  # ~$547k/year
            'transaction_count': 1,
            'marketplace_sales': 0
        })
    
    # Texas - should breach rolling 12m at $500k  
    for i in range(365):
        test_data.append({
            'date': base_date + timedelta(days=i),
            'state': 'TX',
            'gross_sales': 1000,  # ~$365k/year
            'transaction_count': 1,
            'marketplace_sales': 200  # Total $438k - no breach
        })
    
    df = pd.DataFrame(test_data)
    
    # 2. Clean data
    clean_df = DataCleaner.clean(df)
    assert len(clean_df) > 0
    assert 'nexus_sales' in clean_df.columns
    
    # 3. Load config
    config = NexusConfig.from_yaml('src/config/state_config.yaml')
    assert 'CA' in config.states
    
    # 4. Run calculations
    calculator = NexusCalculator(config.states)
    results = []
    
    for state in ['CA', 'TX']:
        if state in config.states:
            result = calculator.analyze_state(state, clean_df)
            results.append(result.to_dict())
    
    # 5. Verify results
    ca_result = next(r for r in results if r['state'] == 'CA')
    assert ca_result['has_nexus'] is True
    assert ca_result['breach_type'] == 'sales'
    assert ca_result['breach_amount'] >= 500000
    
    tx_result = next(r for r in results if r['state'] == 'TX')
    assert tx_result['has_nexus'] is False  # Under threshold
    
    # 6. Export to Excel
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        ExcelExporter.export_results(
            results, 
            clean_df, 
            tmp.name,
            client_name="Test Client"
        )
        
        # Verify file exists and has content
        assert Path(tmp.name).exists()
        assert Path(tmp.name).stat().st_size > 0
        
        # Could add more validation of Excel content here
        
    print("✅ End-to-end test passed!")