#!/usr/bin/env python3
"""
Pedigree Scoring Module
=======================

Scoring system for pedigree JSON comparison:
- Comprehensive score calculation
- Tier-based penalty system
- Score interpretation and breakdown
"""

from typing import Dict, Any
from pedigree_core import calculate_generation_weight


def calculate_comprehensive_score(golden_metrics: Dict[str, int], test_metrics: Dict[str, int], 
                                golden_ext: Dict[str, Any], test_ext: Dict[str, Any]) -> Dict[str, float]:
    """Calculate comprehensive score based on tiered penalty system"""
    
    # Base score
    base_score = 100.0
    
    # TIER 1: Foundation Metrics (50% weight)
    tier1_deductions = 0.0
    
    # Generation Structure (30% of total)
    generations_diff = abs(golden_ext["structural"]["generations_count"] - test_ext["structural"]["generations_count"])
    if generations_diff == 1:
        tier1_deductions += 5
    elif generations_diff >= 2:
        tier1_deductions += 15
    
    # Nodes per level distribution accuracy (generation-weighted)
    golden_levels = golden_ext["structural"]["nodes_per_level"]
    test_levels = test_ext["structural"]["nodes_per_level"]
    all_levels = set(golden_levels.keys()) | set(test_levels.keys())

    # Determine total_levels dynamically from max numeric level
    numeric_levels = [lvl for lvl in all_levels if isinstance(lvl, int) and lvl >= 0]
    max_level = max(numeric_levels) if numeric_levels else 0
    total_levels = max_level + 1

    weighted_level_error = 0.0
    for level in all_levels:
        if not isinstance(level, int) or level < 0:
            continue
        golden_count = golden_levels.get(level, 0)
        test_count = test_levels.get(level, 0)
        diff = abs(golden_count - test_count)
        weight = calculate_generation_weight(level, total_levels)
        weighted_level_error += diff * weight

    # Scale by the same per-node penalty (2 pts) as before
    tier1_deductions += weighted_level_error * 2
    
    # Node Detection (30% of total - with miscarriage adjustment)
    total_nodes_diff = abs(golden_metrics["total_nodes"] - test_metrics["total_nodes"])
    
    # Core People (M/F) Detection (25% of total)
    golden_gender = golden_ext["gender_and_naming"]["gender_distribution"]
    test_gender = test_ext["gender_and_naming"]["gender_distribution"]
    
    mf_diff = (abs(golden_gender.get("MALE", 0) - test_gender.get("MALE", 0)) + 
               abs(golden_gender.get("FEMALE", 0) - test_gender.get("FEMALE", 0)))
    tier1_deductions += mf_diff * 5
    
    # Miscarriage Detection (5% of total) - reduced weight
    miscarriage_diff = abs(golden_gender.get("MISCARRIAGE", 0) - test_gender.get("MISCARRIAGE", 0))
    tier1_deductions += miscarriage_diff * 1
    
    # TIER 2: Relationship Metrics (40% weight)
    tier2_deductions = 0.0
    
    # Parent Relationships (13% of total)
    noparents_diff = abs(golden_metrics["nodes_with_no_parents_true"] - test_metrics["nodes_with_no_parents_true"])
    tier2_deductions += noparents_diff * 4
    
    # Partner Relationships (13% of total)
    partner_diff = (abs(golden_metrics["nodes_with_one_partner"] - test_metrics["nodes_with_one_partner"]) +
                   abs(golden_metrics["nodes_with_multiple_partners"] - test_metrics["nodes_with_multiple_partners"]))
    tier2_deductions += partner_diff * 4
    
    # Sibling Relationships (14% of total)
    # Overall sibling count
    siblings_total_diff = abs(golden_metrics["nodes_with_siblings"] - test_metrics["nodes_with_siblings"])
    tier2_deductions += siblings_total_diff * 4
    
    # Detailed sibling distribution
    sibling_dist_diff = (
        abs(golden_metrics["nodes_with_1_sibling"] - test_metrics["nodes_with_1_sibling"]) +
        abs(golden_metrics["nodes_with_2_siblings"] - test_metrics["nodes_with_2_siblings"]) +
        abs(golden_metrics["nodes_with_3_siblings"] - test_metrics["nodes_with_3_siblings"]) +
        abs(golden_metrics["nodes_with_4_siblings"] - test_metrics["nodes_with_4_siblings"]) +
        abs(golden_metrics["nodes_with_5_or_more_siblings"] - test_metrics["nodes_with_5_or_more_siblings"])
    )
    tier2_deductions += sibling_dist_diff * 4
    
    # TIER 3: Special Attributes (11% weight)
    tier3_deductions = 0.0
    
    # Symbols & Diseases (7% of total)
    # Disease patterns
    golden_diseases = golden_ext["shading"]["disease_counts"]
    test_diseases = test_ext["shading"]["disease_counts"]
    all_diseases = set(golden_diseases.keys()) | set(test_diseases.keys())
    
    for disease in all_diseases:
        disease_diff = abs(golden_diseases.get(disease, 0) - test_diseases.get(disease, 0))
        tier3_deductions += disease_diff * 1
    
    # Status symbols
    golden_symbols = golden_ext["symbols"]["symbol_counts"]
    test_symbols = test_ext["symbols"]["symbol_counts"]
    important_symbols = ["Deceased", "Adopted_in", "Adopted_out"]
    
    for symbol in important_symbols:
        symbol_diff = abs(golden_symbols.get(symbol, 0) - test_symbols.get(symbol, 0))
        tier3_deductions += symbol_diff * 2
    
    # Twin relationships
    dz_diff = abs(golden_ext["edges"]["dztwin_count"] - test_ext["edges"]["dztwin_count"])
    mz_diff = abs(golden_ext["edges"]["mztwin_count"] - test_ext["edges"]["mztwin_count"])
    tier3_deductions += (dz_diff + mz_diff) * 1
    
    # Calculate final score
    total_deductions = (tier1_deductions * 0.50 + 
                       tier2_deductions * 0.40 + 
                       tier3_deductions * 0.10)
    
    final_score = max(0.0, base_score - total_deductions)
    
    return {
        "final_score": final_score,
        "tier1_deductions": tier1_deductions,
        "tier2_deductions": tier2_deductions,
        "tier3_deductions": tier3_deductions,
        "total_deductions": total_deductions,
        "tier1_weighted": tier1_deductions * 0.63,
        "tier2_weighted": tier2_deductions * 0.26,
        "tier3_weighted": tier3_deductions * 0.11
    }


def print_score_breakdown(score_data: Dict[str, float]) -> None:
    """Print detailed score breakdown"""
    print("COMPREHENSIVE SCORE BREAKDOWN")
    print("=" * 50)
    print(f"FINAL SCORE: {score_data['final_score']:.1f}/100")
    print("")
    
    # Score interpretation
    score = score_data['final_score']
    if score >= 90:
        interpretation = "🟢 EXCELLENT - Minor issues only"
    elif score >= 80:
        interpretation = "🟡 GOOD - Some relationship/attribute errors"
    elif score >= 70:
        interpretation = "🟠 ACCEPTABLE - Foundation mostly correct"
    elif score >= 60:
        interpretation = "🔴 POOR - Significant structural problems"
    else:
        interpretation = "FAILING - Major structural failures"
    
    print(f"Interpretation: {interpretation}")
    print("")
    
    print("📋 TIER BREAKDOWN:")
    print(f"   Tier 1 (Foundation 63%):     -{score_data['tier1_weighted']:.1f} pts")
    print(f"   Tier 2 (Relationships 26%):  -{score_data['tier2_weighted']:.1f} pts")
    print(f"   Tier 3 (Attributes 11%):     -{score_data['tier3_weighted']:.1f} pts")
    print(f"   Total Deductions:             -{score_data['total_deductions']:.1f} pts")
    print("") 