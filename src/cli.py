# src/cli.py
"""
Nexus Analyzer CLI - Sales tax nexus detection tool
"""
from pathlib import Path
from typing import Optional
import sys

import click
import pandas as pd
from rich import print
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.config.schema import NexusConfig
from src.data.cleaner import DataCleaner
from src.calculator.nexus import NexusCalculator
from src.export.excel import ExcelExporter
from src.utils.sample_data import SampleDataGenerator

console = Console()

# Create the main CLI group
@click.group()
@click.version_option(version='0.1.0', prog_name='nexus-analyzer')
def cli():
    """
    Nexus Analyzer - Automated sales tax nexus detection
    
    Analyzes sales data to determine where you have economic nexus
    obligations based on state thresholds.
    """
    pass


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('-o', '--output', default='nexus_analysis.xlsx', help='Output Excel file path')
@click.option('-c', '--config', default='src/config/state_config.yaml', help='State config file')
@click.option('--client', default='Client', help='Client name for report')
@click.option('--force-all', is_flag=True, help='Analyze all configured states')
def analyze(input_file, output, config, client, force_all):
    """
    Analyze sales data for nexus determination
    
    INPUT_FILE: Path to CSV file with sales data
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Load configuration
            task = progress.add_task("Loading configuration...", total=None)
            try:
                nexus_config = NexusConfig.from_yaml(config)
                console.print(f"[green]✓[/green] Loaded config for {len(nexus_config.states)} states")
            except Exception as e:
                console.print(f"[red]✗ Error loading config:[/red] {e}")
                sys.exit(1)
            progress.remove_task(task)
            
            # Load sales data
            task = progress.add_task("Loading sales data...", total=None)
            try:
                raw_df = pd.read_csv(input_file)
                console.print(f"[green]✓[/green] Loaded {len(raw_df):,} rows")
            except Exception as e:
                console.print(f"[red]✗ Error loading data:[/red] {e}")
                sys.exit(1)
            progress.remove_task(task)
            
            # Clean data
            task = progress.add_task("Cleaning data...", total=None)
            try:
                clean_df = DataCleaner.clean(raw_df)
                quality = DataCleaner.validate_data_quality(clean_df)
                console.print(f"[green]✓[/green] Data quality score: {quality['data_quality_score']:.0f}%")
            except Exception as e:
                console.print(f"[red]✗ Error cleaning data:[/red] {e}")
                sys.exit(1)
            progress.remove_task(task)
            
            # Run analysis
            task = progress.add_task("Analyzing nexus...", total=None)
            calculator = NexusCalculator(nexus_config.states)
            
            if force_all:
                results = calculator.analyze_all_states(clean_df)
            else:
                # Only analyze states present in data
                states_in_data = clean_df['state'].unique()
                results = []
                for state in states_in_data:
                    if state in nexus_config.states:
                        result = calculator.analyze_state(state, clean_df)
                        results.append(result)
            
            console.print(f"[green]✓[/green] Analyzed {len(results)} states")
            progress.remove_task(task)
            
            # Show summary
            nexus_states = [r for r in results if r.has_nexus]
            if nexus_states:
                console.print(f"\n[bold red]⚠️  Nexus detected in {len(nexus_states)} state(s):[/bold red]")
                for state in nexus_states:
                    console.print(f"  • {state.state}: {state.breach_type} threshold breached on {state.breach_date.strftime('%Y-%m-%d')}")
            else:
                console.print("\n[green]✓ No nexus obligations detected[/green]")
            
            # Export results
            task = progress.add_task("Generating Excel report...", total=None)
            try:
                results_dicts = [r.to_dict() for r in results]
                ExcelExporter.export_results(results_dicts, clean_df, output, client)
                console.print(f"\n[green]✓[/green] Report saved to: [bold]{output}[/bold]")
            except Exception as e:
                console.print(f"[red]✗ Error exporting:[/red] {e}")
                sys.exit(1)
            progress.remove_task(task)
            
        console.print("\n[bold green]Analysis complete![/bold green]")
        
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.option('-o', '--output', default='sample_sales_data.csv', help='Output file path')
@click.option('--start-date', default='2022-01-01', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', default='2023-12-31', help='End date (YYYY-MM-DD)')
@click.option('--states', help='Comma-separated state codes (default: CA,TX,NY,FL,IL,PA,OH,WA)')
@click.option('--force-breach', is_flag=True, help='Inject data to force nexus breaches')
@click.option('--seed', default=42, type=int, help='Random seed for reproducibility')
def generate_sample(output, start_date, end_date, states, force_breach, seed):
    """Generate sample sales data for testing"""
    
    states_list = states.split(',') if states else None
    
    try:
        df = SampleDataGenerator.generate_realistic_data(
            start_date=start_date,
            end_date=end_date,
            states=states_list,
            seed=seed,
            force_breach=force_breach
        )
        
        df.to_csv(output, index=False)
        
        console.print(f"[green]✓[/green] Generated {len(df):,} rows")
        console.print(f"[green]✓[/green] Date range: {start_date} to {end_date}")
        console.print(f"[green]✓[/green] States: {', '.join(df['state'].unique())}")
        if force_breach:
            console.print("[yellow]⚠️  Forced breach data injected[/yellow]")
        console.print(f"[green]✓[/green] Saved to: [bold]{output}[/bold]")
        
    except Exception as e:
        console.print(f"[red]Error generating sample data:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.option('-c', '--config', default='src/config/state_config.yaml', help='State config file')
@click.option('--verbose', is_flag=True, help='Show detailed thresholds')
def states(config, verbose):
    """List configured states and their thresholds"""
    
    try:
        nexus_config = NexusConfig.from_yaml(config)
        
        table = Table(title="Configured States", show_header=True)
        table.add_column("State", style="cyan", width=8)
        table.add_column("Sales Threshold", justify="right", style="green")
        table.add_column("Transaction Threshold", justify="right", style="yellow")
        table.add_column("Lookback Rule", style="blue")
        
        if verbose:
            table.add_column("Tax Rate", justify="right")
            table.add_column("Marketplace", style="magenta")
        
        for state, cfg in sorted(nexus_config.states.items()):
            sales = f"${cfg.sales_threshold:,.0f}" if cfg.sales_threshold else "—"
            trans = f"{cfg.transaction_threshold:,}" if cfg.transaction_threshold else "—"
            
            if verbose:
                table.add_row(
                    state, sales, trans, cfg.lookback_rule,
                    f"{cfg.tax_rate:.2%}",
                    "✓" if cfg.marketplace_threshold_inclusion else "✗"
                )
            else:
                table.add_row(state, sales, trans, cfg.lookback_rule)
        
        console.print(table)
        
        # Summary stats
        summary = nexus_config.summary_report()
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  • Total states: {summary['total_states']}")
        console.print(f"  • With sales threshold: {summary['states_with_sales_threshold']}")
        console.print(f"  • With transaction threshold: {summary['states_with_transaction_threshold']}")
        
    except Exception as e:
        console.print(f"[red]Error loading config:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument('state')
@click.option('-c', '--config', default='src/config/state_config.yaml', help='State config file')
def state_info(state, config):
    """Show detailed information for a specific state"""
    
    state = state.upper()
    
    try:
        nexus_config = NexusConfig.from_yaml(config)
        
        if state not in nexus_config.states:
            console.print(f"[red]State '{state}' not found in configuration[/red]")
            console.print(f"Available states: {', '.join(sorted(nexus_config.states.keys()))}")
            sys.exit(1)
        
        cfg = nexus_config.states[state]
        
        console.print(f"\n[bold cyan]{state} - Nexus Configuration[/bold cyan]")
        console.print("=" * 40)
        
        console.print(f"\n[bold]Thresholds:[/bold]")
        console.print(f"  • Sales: ${cfg.sales_threshold:,.0f}" if cfg.sales_threshold else "  • Sales: Not applicable")
        console.print(f"  • Transactions: {cfg.transaction_threshold:,}" if cfg.transaction_threshold else "  • Transactions: Not applicable")
        
        console.print(f"\n[bold]Rules:[/bold]")
        console.print(f"  • Lookback: {cfg.lookback_rule}")
        console.print(f"  • Include marketplace sales: {'Yes' if cfg.marketplace_threshold_inclusion else 'No'}")
        
        console.print(f"\n[bold]Tax Information:[/bold]")
        console.print(f"  • Tax rate: {cfg.tax_rate:.2%}")
        console.print(f"  • Standard penalty: {cfg.standard_penalty_rate:.0%}")
        console.print(f"  • Interest rate: {cfg.interest_rate:.1%} annually")
        
        if cfg.effective_date:
            console.print(f"\n[bold]Effective:[/bold] {cfg.effective_date}")
        
        if cfg.notes:
            console.print(f"\n[bold]Notes:[/bold] {cfg.notes}")
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
def test():
    """Run a quick test with sample data"""
    
    console.print("[bold]Running quick nexus analysis test...[/bold]\n")
    
    # Generate test data
    with console.status("Generating test data..."):
        df = SampleDataGenerator.generate_realistic_data(
            start_date='2023-01-01',
            end_date='2023-12-31',
            states=['CA', 'TX', 'FL'],
            force_breach=True
        )
    
    console.print(f"[green]✓[/green] Generated {len(df):,} rows of test data")
    
    # Clean and analyze
    with console.status("Running analysis..."):
        clean_df = DataCleaner.clean(df)
        config = NexusConfig.from_yaml('src/config/state_config.yaml')
        calculator = NexusCalculator(config.states)
        results = calculator.analyze_all_states(clean_df)
    
    # Show results
    table = Table(title="Test Results")
    table.add_column("State", style="cyan")
    table.add_column("Has Nexus", style="red")
    table.add_column("Breach Date")
    table.add_column("Type")
    table.add_column("Amount", justify="right")
    
    for r in sorted(results, key=lambda x: (not x.has_nexus, x.state)):
        table.add_row(
            r.state,
            "Yes" if r.has_nexus else "No",
            r.breach_date.strftime('%Y-%m-%d') if r.breach_date else "—",
            r.breach_type or "—",
            f"${r.breach_amount:,.0f}" if r.breach_amount else "—"
        )
    
    console.print("\n")
    console.print(table)
    console.print("\n[green]Test complete![/green]")


# Entry point for direct execution
if __name__ == '__main__':
    cli()