#!/usr/bin/env python3
"""
Pedigree Core Module
===================

Core functionality for pedigree JSON processing:
- JSON file loading and validation
- Node extraction and basic metrics
- Extended metrics computation
"""

import json
import sys
import os
from typing import Dict, List, Any, Set
from collections import Counter


def load_json_file(file_path: str) -> Dict:
    """Load and validate JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file {file_path}: {e}")


def extract_nodes(json_data: Dict) -> List[Dict[str, Any]]:
    """Extract pedigree nodes from various JSON structures"""
    if isinstance(json_data, dict) and "original_json" in json_data and "json" in json_data["original_json"]:
        return json_data["original_json"]["json"]
    if isinstance(json_data, list):
        return json_data
    if isinstance(json_data, dict) and "json" in json_data:
        return json_data["json"]
    raise ValueError("Unable to extract pedigree nodes from JSON structure")


# Removed count_parents function as it's no longer needed


def calculate_generation_weight(level: int, total_levels: int) -> float:
    """
    Calculate weight for a generation level dynamically.
    Higher weight for top levels, gradually decreasing.

    Uses exponential decay and normalizes weights so that
    the sum of weights across 0..total_levels-1 equals 1.0
    """
    # Exponential decay base weight
    raw = 1.0 / (1.2 ** max(level, 0))
    # Normalize across all levels
    denom = sum(1.0 / (1.2 ** l) for l in range(max(total_levels, 1))) or 1.0
    return raw / denom


def compute_metrics(nodes: List[Dict[str, Any]]) -> Dict[str, int]:
    """Compute basic metrics for pedigree nodes"""
    total_nodes = len(nodes)

    # Flags
    nodes_with_noparents_true = sum(1 for n in nodes if bool(n.get("noparents")))
    
    # Partner counts
    nodes_with_one_partner = sum(1 for n in nodes if isinstance(n.get("partners"), list) and len(n.get("partners")) == 1)
    nodes_with_multiple_partners = sum(1 for n in nodes if isinstance(n.get("partners"), list) and len(n.get("partners")) > 1)
    
    # Sibling counts
    nodes_with_siblings = 0
    sibling_counts = {1: 0, 2: 0, 3: 0, 4: 0, "5+": 0}
    for n in nodes:
        siblings = n.get("siblings", [])
        if isinstance(siblings, list) and siblings:
            sibling_count = len(siblings)
            nodes_with_siblings += 1
            if sibling_count >= 5:
                sibling_counts["5+"] += 1
            else:
                sibling_counts[sibling_count] += 1

    return {
        "total_nodes": total_nodes,
        "nodes_with_no_parents_true": nodes_with_noparents_true,
        "nodes_with_one_partner": nodes_with_one_partner,
        "nodes_with_multiple_partners": nodes_with_multiple_partners,
        "nodes_with_siblings": nodes_with_siblings,
        "nodes_with_1_sibling": sibling_counts[1],
        "nodes_with_2_siblings": sibling_counts[2],
        "nodes_with_3_siblings": sibling_counts[3],
        "nodes_with_4_siblings": sibling_counts[4],
        "nodes_with_5_or_more_siblings": sibling_counts["5+"],
    }


def print_metrics(label: str, metrics: Dict[str, int]) -> None:
    """Print basic metrics in formatted output"""
    print(f"{label}:")
    print("-" * 40)
    print(f"No of Total nodes: {metrics['total_nodes']}")
    print(f"No of nodes with no_parents true: {metrics['nodes_with_no_parents_true']}")
    print(f"No of nodes with exactly one partner: {metrics['nodes_with_one_partner']}")
    print(f"No of nodes with multiple partners: {metrics['nodes_with_multiple_partners']}")
    print(f"\nSibling Distribution:")
    print(f"Total nodes with siblings: {metrics['nodes_with_siblings']}")
    print(f"  - With 1 sibling: {metrics['nodes_with_1_sibling']}")
    print(f"  - With 2 siblings: {metrics['nodes_with_2_siblings']}")
    print(f"  - With 3 siblings: {metrics['nodes_with_3_siblings']}")
    print(f"  - With 4 siblings: {metrics['nodes_with_4_siblings']}")
    print(f"  - With 5 or more siblings: {metrics['nodes_with_5_or_more_siblings']}")
    print("")


def _unique_sorted_pairs(pairs: List[List[str]]) -> Set[tuple]:
    """Extract unique sorted pairs from list of pairs"""
    unique_pairs: Set[tuple] = set()
    for pair in pairs:
        if not pair or len(pair) < 1:
            continue
        # allow both single value and list
        if isinstance(pair, list) and len(pair) == 2:
            a, b = pair[0], pair[1]
        else:
            # unsupported shape
            continue
        if a and b and a != b:
            unique_pairs.add(tuple(sorted((a, b))))
    return unique_pairs


def compute_extended_metrics(nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute comprehensive extended metrics for pedigree analysis"""
    # Levels and basic distributions
    level_dist: Counter = Counter()
    for n in nodes:
        # Only count in level distribution if it's level 0 with top_level true
        # or if it's any other level regardless of top_level
        if n.get("level") != 0 or (n.get("level") == 0 and bool(n.get("top_level"))):
            level_dist[n.get("level")] += 1
    generations_count = len(level_dist)
    level_counts = dict(sorted(level_dist.items(), key=lambda kv: (kv[0] is None, kv[0])))

    # Parent-child relations (needed for other calculations)
    parent_to_children: Dict[str, List[str]] = {}
    for n in nodes:
        child_name = n.get("name")
        for p in (n.get("father"), n.get("mother")):
            if p:
                parent_to_children.setdefault(p, []).append(child_name)

    # Gender and naming - updated for new node types
    gender_dist: Counter = Counter()
    for n in nodes:
        # Check for miscarriage flag first
        if bool(n.get("miscarriage")):
            gender_dist["MISCARRIAGE"] += 1
        else:
            # Then check sex
            sex = n.get("sex")
            if sex == "M":
                gender_dist["MALE"] += 1
            elif sex == "F":
                gender_dist["FEMALE"] += 1
            else:
                gender_dist["UNKNOWN"] += 1

    # Partnerships and divorces
    partners_map: Dict[str, Set[str]] = {}
    for n in nodes:
        name = n.get("name")
        partners = n.get("partners") or []
        if isinstance(partners, list):
            partners_map.setdefault(name, set()).update([p for p in partners if p and p != name])

    partnership_pairs: Set[tuple] = set()
    for a, partners in partners_map.items():
        for b in partners:
            if a and b and a != b:
                partnership_pairs.add(tuple(sorted((a, b))))

    divorces_pairs: Set[tuple] = set()
    for n in nodes:
        name = n.get("name")
        divs = n.get("divorced") or []
        if isinstance(divs, list):
            for d in divs:
                if d and d != name:
                    divorces_pairs.add(tuple(sorted((name, d))))

    # Parents completeness and children distribution
    zero_parents = one_parent = two_parents = 0
    for n in nodes:
        cnt = int(bool(n.get("father"))) + int(bool(n.get("mother")))
        if cnt == 0:
            zero_parents += 1
        elif cnt == 1:
            one_parent += 1
        else:
            two_parents += 1



    # Diseases and Symbols
    # Model disease patterns (UPPERCASE_WITH_UNDERSCORES format)
    model_disease_patterns = [
        'CIRCLE_BOTTOM_HALF_FILLED', 'CIRCLE_CHECKERED', 'CIRCLE_CROSS_FILLED', 'CIRCLE_DIAGONAL_CHECKERED', 
        'CIRCLE_DIAGONAL_STROKES', 'CIRCLE_FILLED', 'CIRCLE_HORIZONTAL_STROKES', 'CIRCLE_LEFT_HALF_FILLED', 
        'CIRCLE_RIGHT_HALF_FILLED', 'CIRCLE_TOP_HALF_FILLED', 'CIRCLE_TOP_HALF_STROKES', 
        'CIRCLE_TOP_LEFT_QUARTER_FILLED', 'CIRCLE_TOP_RIGHT_QUARTER_FILLED', 'CIRCLE_VERTICAL_STROKES',
        'SQUARE_BOTTOM_HALF_FILLED', 'SQUARE_CHECKERED', 'SQUARE_CROSS_FILLED', 'SQUARE_DIAGONAL_CHECKERED',
        'SQUARE_DIAGONAL_STROKES', 'SQUARE_FILLED', 'SQUARE_HORIZONTAL_STROKES', 'SQUARE_LEFT_FILLED',
        'SQUARE_RIGHT_FILLED', 'SQUARE_TOP_HALF_FILLED', 'SQUARE_TOP_HALF_STROKES',
        'SQUARE_TOP_LEFT_QUARTER_FILLED', 'SQUARE_TOP_RIGHT_QUARTER_FILLED', 'SQUARE_VERTICAL_STROKES'
    ]
    
    # Symbol types
    symbol_types = ['Adopted_in', 'Adopted_out', 'Carrier', 'Deceased', 'Divorce', 'Patient']
    
    disease_counts: Counter = Counter()
    symbol_counts: Counter = Counter()
    
    for n in nodes:
        sex = n.get("sex")
        shading_list = n.get("shading")
        
        # Count disease patterns by combining sex + shading
        # Skip miscarriage nodes as they don't have traditional M/F sex for disease patterns
        if shading_list and sex in ("M", "F") and not bool(n.get("miscarriage")):
            # Determine shape based on sex
            shape = "SQUARE" if sex == "M" else "CIRCLE"
            
            def process_shading_pattern(pattern: str) -> str:
                # Remove 'female' suffix if present and convert to uppercase with underscores
                pattern = pattern.replace(" female", "")
                pattern_upper = pattern.upper().replace("-", "_")
                return f"{shape}_{pattern_upper}"

            if isinstance(shading_list, list):
                for shading_pattern in shading_list:
                    full_disease = process_shading_pattern(shading_pattern)
                    # Only count if it's in the model's disease patterns
                    if full_disease in model_disease_patterns:
                        disease_counts[full_disease] += 1
            elif isinstance(shading_list, str):
                full_disease = process_shading_pattern(shading_list)
                if full_disease in model_disease_patterns:
                    disease_counts[full_disease] += 1
        
        # Count symbols
        if n.get("status") == 1:  # Deceased
            symbol_counts["Deceased"] += 1
        if bool(n.get("adopted_in")):
            symbol_counts["Adopted_in"] += 1
        if bool(n.get("adopted_out")):
            symbol_counts["Adopted_out"] += 1
        if n.get("divorced"):  # Divorce
            symbol_counts["Divorce"] += 1
        if bool(n.get("proband")):  # Patient (proband)
            symbol_counts["Patient"] += 1
        # Note: Carrier would need specific field in JSON to detect


    return {
        "structural": {
            "generations_count": generations_count,
            "nodes_per_level": level_counts
        },
        "gender_and_naming": {
            "gender_distribution": dict(gender_dist),
        },
        "partnerships": {
            "partnerships_count": len(partnership_pairs),
            "divorces_count": len(divorces_pairs)
        },
        "parent_child_and_siblings": {
            "parents_completeness": {
                "zero_parents": zero_parents,
                "one_parent": one_parent,
                "two_parents": two_parents,
            }
        },
        "shading": {
            "disease_counts": dict(disease_counts),
        },
        "symbols": {
            "symbol_counts": dict(symbol_counts),
        },
        "edges": {
            "dztwin_count": sum(1 for n in nodes if n.get("dztwin") == 1),
            "mztwin_count": sum(1 for n in nodes if n.get("mztwin") == 1),
        }
    } 