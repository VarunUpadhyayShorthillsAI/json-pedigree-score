#!/usr/bin/env python3
"""
Pedigree Export Module
======================

Excel export functionality for pedigree comparison results:
- Basic metrics export
- Extended metrics export with multiple sheets
- Score summary export
"""

from typing import Dict, Any

# Check if pandas is available
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: pandas not available. Install with: pip install pandas openpyxl")
    print("Excel export will be disabled, but console report will still work.")



def export_extended_to_excel(excel_file: str, golden_ext: Dict[str, Any], test_ext: Dict[str, Any], 
                           golden_metrics: Dict[str, int], test_metrics: Dict[str, int], 
                           score_data: Dict[str, float]) -> None:
    """Export comprehensive extended metrics to Excel with multiple sheets"""
    if not PANDAS_AVAILABLE:
        return
    try:
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            # Score Summary Sheet
            score_rows = [
                {"Metric": "Final Score", "Value": f"{score_data['final_score']:.1f}/100", "Details": ""},
                {"Metric": "Tier 1 (Foundation)", "Value": f"-{score_data['tier1_weighted']:.1f} pts", "Details": "Generation structure + Node detection"},
                {"Metric": "Tier 2 (Relationships)", "Value": f"-{score_data['tier2_weighted']:.1f} pts", "Details": "Family connections + Partnerships"},
                {"Metric": "Tier 3 (Attributes)", "Value": f"-{score_data['tier3_weighted']:.1f} pts", "Details": "Symbols + Diseases + Twins"},
                {"Metric": "Total Deductions", "Value": f"-{score_data['total_deductions']:.1f} pts", "Details": "Sum of all penalties"}
            ]
            pd.DataFrame(score_rows).to_excel(writer, sheet_name='Score Summary', index=False)

            # Generation (renamed from Structural)
            rows = []
            def add_row(metric, gval, tval):
                rows.append({
                    "Metric": metric,
                    "Golden": gval,
                    "Test": tval,
                    "Difference": abs(gval - tval) if isinstance(gval, (int, float)) and isinstance(tval, (int, float)) else "",
                })
            gs = golden_ext["structural"]
            ts = test_ext["structural"]
            add_row("Generations Count", gs["generations_count"], ts["generations_count"])
            # nodes per level (union of levels)
            levels = sorted(set(gs["nodes_per_level"].keys()) | set(ts["nodes_per_level"].keys()), key=lambda x: (x is None, x))
            for lvl in levels:
                g = gs["nodes_per_level"].get(lvl, 0)
                t = ts["nodes_per_level"].get(lvl, 0)
                add_row(f"Nodes at level {lvl}", g, t)
            pd.DataFrame(rows).to_excel(writer, sheet_name='Generation', index=False)

            # Nodes (combining general metrics + gender)
            rows = []
            
            # Add general metrics first
            for key in golden_metrics.keys():
                add_row(key.replace('_', ' ').title(), golden_metrics[key], test_metrics[key])
            
            # Add gender distribution
            gg = golden_ext["gender_and_naming"]
            tg = test_ext["gender_and_naming"]
            for sex in sorted(set(gg["gender_distribution"].keys()) | set(tg["gender_distribution"].keys())):
                add_row(f"{sex}", gg["gender_distribution"].get(sex, 0), tg["gender_distribution"].get(sex, 0))
            pd.DataFrame(rows).to_excel(writer, sheet_name='Nodes', index=False)

            # Diseases (show all possible disease patterns)
            rows = []
            gd = golden_ext["shading"]
            td = test_ext["shading"]
            
            # Calculate total nodes with any disease/shading
            golden_total = sum(gd["disease_counts"].values())
            test_total = sum(td["disease_counts"].values())
            add_row("Total Nodes With Disease/Shading", golden_total, test_total)
            rows.append({"Metric": "", "Golden": "", "Test": "", "Difference": ""})  # Empty row for spacing
            
            # All possible disease patterns from model
            all_disease_patterns = [
                'CIRCLE_BOTTOM_HALF_FILLED', 'CIRCLE_CHECKERED', 'CIRCLE_CROSS_FILLED', 'CIRCLE_DIAGONAL_CHECKERED', 
                'CIRCLE_DIAGONAL_STROKES', 'CIRCLE_FILLED', 'CIRCLE_HORIZONTAL_STROKES', 'CIRCLE_LEFT_HALF_FILLED', 
                'CIRCLE_RIGHT_HALF_FILLED', 'CIRCLE_TOP_HALF_FILLED', 'CIRCLE_TOP_HALF_STROKES', 
                'CIRCLE_TOP_LEFT_QUARTER_FILLED', 'CIRCLE_TOP_RIGHT_QUARTER_FILLED', 'CIRCLE_VERTICAL_STROKES',
                'SQUARE_BOTTOM_HALF_FILLED', 'SQUARE_CHECKERED', 'SQUARE_CROSS_FILLED', 'SQUARE_DIAGONAL_CHECKERED',
                'SQUARE_DIAGONAL_STROKES', 'SQUARE_FILLED', 'SQUARE_HORIZONTAL_STROKES', 'SQUARE_LEFT_FILLED',
                'SQUARE_RIGHT_FILLED', 'SQUARE_TOP_HALF_FILLED', 'SQUARE_TOP_HALF_STROKES',
                'SQUARE_TOP_LEFT_QUARTER_FILLED', 'SQUARE_TOP_RIGHT_QUARTER_FILLED', 'SQUARE_VERTICAL_STROKES'
            ]
            for pattern in sorted(all_disease_patterns):
                add_row(f"{pattern}", gd["disease_counts"].get(pattern, 0), td["disease_counts"].get(pattern, 0))
            pd.DataFrame(rows).to_excel(writer, sheet_name='Diseases', index=False)

            # Symbols (show all possible symbols)
            rows = []
            gs = golden_ext["symbols"]
            ts = test_ext["symbols"]
            # All possible symbol types
            all_symbol_types = ['Adopted_in', 'Adopted_out', 'Carrier', 'Deceased', 'Divorce', 'Patient']
            for symbol in sorted(all_symbol_types):
                add_row(f"{symbol}", gs["symbol_counts"].get(symbol, 0), ts["symbol_counts"].get(symbol, 0))
            pd.DataFrame(rows).to_excel(writer, sheet_name='Symbols', index=False)

            # Edges (twin relationships)
            rows = []
            ge = golden_ext["edges"]
            te = test_ext["edges"]
            add_row("DZ Twin (Dizygotic) Count", ge["dztwin_count"], te["dztwin_count"])
            add_row("MZ Twin (Monozygotic) Count", ge["mztwin_count"], te["mztwin_count"])
            pd.DataFrame(rows).to_excel(writer, sheet_name='Edges', index=False)

            # Adjust widths
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except Exception:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
        print(f"✅ Excel extended sheets appended to: {excel_file}")
    except Exception as e:
        print(f"❌ Error exporting extended Excel: {e}") 