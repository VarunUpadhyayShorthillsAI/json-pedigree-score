#!/usr/bin/env python3
"""
Pedigree JSON Comparator - Main Script
=====================================

Main execution script for pedigree JSON comparison.
This script orchestrates the entire comparison process:
1. Loads golden and test JSON files
2. Computes basic and extended metrics
3. Calculates comprehensive scores
4. Exports results to Excel

Usage:
    python pedigree_main.py
"""

import sys
import os

# Import our modules
from pedigree_core import (
    load_json_file, 
    extract_nodes, 
    compute_metrics, 
    print_metrics, 
    compute_extended_metrics
)
from pedigree_scoring import calculate_comprehensive_score, print_score_breakdown
from pedigree_export import export_extended_to_excel  # Handles all Excel exports


def main() -> None:
    """Main execution function"""
    golden_file = "golden.json"
    test_file = "test.json"
    
    # Check if input files exist
    if not os.path.exists(golden_file):
        print(f"Error: {golden_file} not found")
        sys.exit(1)
    if not os.path.exists(test_file):
        print(f"Error: {test_file} not found")  
        sys.exit(1)
        
    try:
        # Load and extract data
        print("Loading JSON files...")
        golden_data = load_json_file(golden_file)
        test_data = load_json_file(test_file)
        golden_nodes = extract_nodes(golden_data)
        test_nodes = extract_nodes(test_data)

        # Compute basic metrics
        print("Computing basic metrics...")
        golden_metrics = compute_metrics(golden_nodes)
        test_metrics = compute_metrics(test_nodes)

        # Print basic metrics
        print_metrics("Golden JSON Metrics", golden_metrics)
        print_metrics("Test JSON Metrics", test_metrics)
        
        # Compute extended analytics
        print("Computing extended analytics...")
        golden_ext = compute_extended_metrics(golden_nodes)
        test_ext = compute_extended_metrics(test_nodes)
        
        # Calculate comprehensive score
        print("Calculating comprehensive score...")
        score_data = calculate_comprehensive_score(golden_metrics, test_metrics, golden_ext, test_ext)
        print_score_breakdown(score_data)
        
        # Export to Excel
        print("Exporting results to Excel...")
        export_extended_to_excel("comparison_results.xlsx", golden_ext, test_ext, golden_metrics, test_metrics, score_data)
        
        print("Analysis complete!")
        
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 