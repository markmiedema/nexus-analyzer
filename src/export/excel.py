# Standardized Excel output
import pandas as pd
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from typing import List

class ExcelExporter:
    """Export to standardized Excel template"""
    
    TEMPLATE_PATH = "templates/nexus_analysis_template.xlsx"
    
    # Standardized sheet names
    SUMMARY_SHEET = "Nexus Summary"
    DETAILS_SHEET = "State Details"
    DATA_SHEET = "Source Data"
    
    @staticmethod
    def export_results(
        results: List[dict],
        sales_data: pd.DataFrame,
        output_path: str,
        client_name: str = "Client"
    ):
        """Export analysis results to Excel"""
        
        # Convert results to DataFrame
        results_df = pd.DataFrame(results)
        
        # Create summary statistics
        summary_stats = {
            'Total States Analyzed': len(results_df),
            'States with Nexus': len(results_df[results_df['has_nexus']]),
            'Earliest Breach': results_df[results_df['has_nexus']]['breach_date'].min() if any(results_df['has_nexus']) else 'None',
            'Analysis Date': pd.Timestamp.now().strftime('%Y-%m-%d')
        }
        
        # Write to Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 1. Summary sheet
            summary_df = pd.DataFrame(list(summary_stats.items()), columns=['Metric', 'Value'])
            summary_df.to_excel(writer, sheet_name=ExcelExporter.SUMMARY_SHEET, index=False)
            
            # 2. Detailed results
            results_df.to_excel(writer, sheet_name=ExcelExporter.DETAILS_SHEET, index=False)
            
            # 3. Source data sample (first 1000 rows)
            sales_data.head(1000).to_excel(writer, sheet_name=ExcelExporter.DATA_SHEET, index=False)
            
            # Format the workbook
            workbook = writer.book
            
            # Format summary sheet
            summary_ws = workbook[ExcelExporter.SUMMARY_SHEET]
            summary_ws.column_dimensions['A'].width = 25
            summary_ws.column_dimensions['B'].width = 20
            
            # Add title
            summary_ws.insert_rows(1)
            summary_ws.merge_cells('A1:B1')
            summary_ws['A1'] = f'Nexus Analysis Summary - {client_name}'
            summary_ws['A1'].font = Font(size=16, bold=True)
            summary_ws['A1'].alignment = Alignment(horizontal='center')
            
            # Format details sheet
            details_ws = workbook[ExcelExporter.DETAILS_SHEET]
            
            # Header formatting
            for cell in details_ws[1]:
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                cell.font = Font(color="FFFFFF", bold=True)
            
            # Conditional formatting for nexus states
            for row in range(2, len(results_df) + 2):
                if details_ws[f'B{row}'].value:  # has_nexus = True
                    for col in ['A', 'B', 'C', 'D', 'E', 'F']:
                        details_ws[f'{col}{row}'].fill = PatternFill(
                            start_color="FFE6E6", end_color="FFE6E6", fill_type="solid"
                        )
            
            # Auto-fit columns
            for column in details_ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                details_ws.column_dimensions[column_letter].width = adjusted_width