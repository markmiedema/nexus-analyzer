# tests/test_integration.py
import pytest
import tempfile
from pathlib import Path
import pandas as pd
from click.testing import CliRunner

from src.cli import cli
from src.utils.sample_data import SampleDataGenerator

def test_cli_full_workflow():
    """Test complete CLI workflow"""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
# Generate sample data
        sample_file = Path(tmpdir) / 'sample.csv'
        result = runner.invoke(cli, ['generate-sample', '-o', str(sample_file)])
        assert result.exit_code == 0
        assert sample_file.exists()

# Run analysis
        output_file = Path(tmpdir) / 'report.xlsx'
        result = runner.invoke(cli, [
            'analyze',
            str(sample_file),
            '-o', str(output_file),
            '--client', 'Test Client'
        ])
        assert result.exit_code == 0
        assert output_file.exists()
        assert 'Analysis complete!' in result.output

def test_states_command():
    """Test states listing command"""
    runner = CliRunner()
    result = runner.invoke(cli, ['states'])
    assert result.exit_code == 0
    assert 'CA' in result.output
    assert '$500,000' in result.output