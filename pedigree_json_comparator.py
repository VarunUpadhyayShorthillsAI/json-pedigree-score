#!/usr/bin/env python3
"""
Pedigree JSON Metrics (Simplified)
==================================

Computes ONLY the following counts for both JSONs (golden and test):
- No of Total nodes
- No of nodes in single generation (levels that contain exactly one node)
- No of nodes with no_parents true
- No of nodes having top_level true
- No of nodes having partner (Spouse)
- No of nodes having child
- No of independent nodes (no parents, no partners, and no children)
- No of special nodes (any of: deceased/status==1, adopted_in, adopted_out, shading, top_level, noparents)

Usage:
    python pedigree_json_comparator.py
"""

import json
import sys
import os
from typing import Dict, List, Any, Set
from collections import Counter

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("⚠️  Warning: pandas not available. Install with: pip install pandas openpyxl")
    print("   Excel export will be disabled, but console report will still work.")


from pedigree_core import load_json_file, extract_nodes


def count_parents(json_passed: List[Dict[str, Any]]) -> tuple:
    """Count how many nodes have mother/father fields"""
    mother, father = 0, 0
    for object in json_passed:
        if 'mother' in object:
            mother += 1
        if 'father' in object:
            father += 1
    return mother, father


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
    total_nodes = len(nodes)

    # Remove single generation calculation

    # Flags
    nodes_with_noparents_true = sum(1 for n in nodes if bool(n.get("noparents")))
    nodes_with_top_level_true = sum(1 for n in nodes if bool(n.get("top_level")))
    nodes_with_partner = sum(1 for n in nodes if isinstance(n.get("partners"), list) and len(n.get("partners")) > 0)

    # Parents/children relationships
    name_set: Set[str] = {n.get("name") for n in nodes}
    parent_names: Set[str] = set()
    for n in nodes:
        father = n.get("father")
        mother = n.get("mother")
        if father:
            parent_names.add(father)
        if mother:
            parent_names.add(mother)
    nodes_with_child = len(parent_names & name_set)

    # Parent counts
    mother_count, father_count = count_parents(nodes)

    # Remove independent nodes and special nodes calculations

    return {
        "total_nodes": total_nodes,
        "nodes_with_no_parents_true": nodes_with_noparents_true,
        "nodes_with_top_level_true": nodes_with_top_level_true,
        "nodes_with_partner": nodes_with_partner,
        "nodes_with_child": nodes_with_child,
        "nodes_with_mother": mother_count,
        "nodes_with_father": father_count,
    }


def print_metrics(label: str, metrics: Dict[str, int]) -> None:
    print(f"{label}:")
    print("-" * 40)
    print(f"No of Total nodes: {metrics['total_nodes']}")
    print(f"No of nodes with no_parents true: {metrics['nodes_with_no_parents_true']}")
    print(f"No of nodes having top_level true: {metrics['nodes_with_top_level_true']}")
    print(f"No of nodes having partner (Spouse): {metrics['nodes_with_partner']}")
    print(f"No of nodes having child: {metrics['nodes_with_child']}")
    print(f"No of nodes with mother: {metrics['nodes_with_mother']}")
    print(f"No of nodes with father: {metrics['nodes_with_father']}")
    print("")


def _unique_sorted_pairs(pairs: List[List[str]]) -> Set[tuple]:
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
    name_to_node: Dict[str, Dict[str, Any]] = {n.get("name"): n for n in nodes}

    # Levels and basic distributions
    level_dist: Counter = Counter()
    for n in nodes:
        level_dist[n.get("level")] += 1
    generations_count = len(level_dist)
    level_counts = dict(sorted(level_dist.items(), key=lambda kv: (kv[0] is None, kv[0])))
    per_level_sizes = list(level_dist.values())
    per_level_min = min(per_level_sizes) if per_level_sizes else 0
    per_level_max = max(per_level_sizes) if per_level_sizes else 0
    per_level_avg = (sum(per_level_sizes) / len(per_level_sizes)) if per_level_sizes else 0.0

    # Parent-child relations
    parent_to_children: Dict[str, List[str]] = {}
    all_children: Set[str] = set()
    parent_names: Set[str] = set()
    for n in nodes:
        child_name = n.get("name")
        for p in (n.get("father"), n.get("mother")):
            if p:
                parent_names.add(p)
                parent_to_children.setdefault(p, []).append(child_name)
                all_children.add(child_name)

    root_nodes_count = sum(1 for n in nodes if not n.get("father") and not n.get("mother"))
    leaf_nodes_count = sum(1 for n in nodes if n.get("name") not in parent_names)

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

    avg_partners_per_node = sum(len(s) for s in partners_map.values()) / max(len(nodes), 1)
    max_partners_for_single_node = max((len(s) for s in partners_map.values()), default=0)

    divorces_pairs: Set[tuple] = set()
    for n in nodes:
        name = n.get("name")
        divs = n.get("divorced") or []
        if isinstance(divs, list):
            for d in divs:
                if d and d != name:
                    divorces_pairs.add(tuple(sorted((name, d))))

    partnered_nodes_count = sum(1 for s in partners_map.values() if len(s) > 0)
    divorce_rate = (len(divorces_pairs) / max(len(partnership_pairs), 1)) * 100.0 if partnership_pairs else 0.0

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

    children_counts = [len(children) for children in parent_to_children.values()]
    min_children = min(children_counts) if children_counts else 0
    max_children = max(children_counts) if children_counts else 0
    avg_children = (sum(children_counts) / len(children_counts)) if children_counts else 0.0

    # Sibling groups
    sibling_groups: List[Set[str]] = []
    for n in nodes:
        name = n.get("name")
        sibs = n.get("siblings") or []
        if sibs:
            group = set([name] + [s for s in sibs if s])
            if len(group) > 1:
                fg = frozenset(group)
                if fg not in [frozenset(g) for g in sibling_groups]:
                    sibling_groups.append(group)
    sibling_group_sizes = [len(g) for g in sibling_groups]
    sibling_groups_count = len(sibling_groups)
    sibling_min = min(sibling_group_sizes) if sibling_group_sizes else 0
    sibling_max = max(sibling_group_sizes) if sibling_group_sizes else 0
    sibling_avg = (sum(sibling_group_sizes) / len(sibling_group_sizes)) if sibling_group_sizes else 0.0

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
            
            if isinstance(shading_list, list):
                for shading_pattern in shading_list:
                    # Convert lowercase-hyphen to UPPERCASE_UNDERSCORE format
                    pattern_upper = shading_pattern.upper().replace("-", "_")
                    full_disease = f"{shape}_{pattern_upper}"
                    
                    # Only count if it's in the model's disease patterns
                    if full_disease in model_disease_patterns:
                        disease_counts[full_disease] += 1
            elif isinstance(shading_list, str):
                pattern_upper = shading_list.upper().replace("-", "_")
                full_disease = f"{shape}_{pattern_upper}"
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

    # Consistency checks
    issues_self_ref: List[str] = []
    issues_duplicates: List[str] = []
    issues_contradictions: List[str] = []
    issues_partner_asym: List[str] = []
    issues_sibling_asym: List[str] = []

    # Duplicate names
    name_counts: Counter = Counter(n.get("name") for n in nodes)
    for nm, c in name_counts.items():
        if c > 1:
            issues_duplicates.append(f"Duplicate name '{nm}' appears {c} times")

    # Self-refs and contradictions
    for n in nodes:
        name = n.get("name")
        father = n.get("father")
        mother = n.get("mother")
        if father:
            if father == name:
                issues_self_ref.append(f"{name}: self-referenced as father")
        if mother:
            if mother == name:
                issues_self_ref.append(f"{name}: self-referenced as mother")
        partners = n.get("partners") or []
        if isinstance(partners, list) and name in partners:
            issues_self_ref.append(f"{name}: self-referenced as partner")
        sibs = n.get("siblings") or []
        if isinstance(sibs, list) and name in sibs:
            issues_self_ref.append(f"{name}: self-referenced as sibling")
        if bool(n.get("noparents")) and (father or mother):
            issues_contradictions.append(f"{name}: noparents==true but has parents listed")
        if bool(n.get("top_level")) and (father or mother):
            issues_contradictions.append(f"{name}: top_level==true but has parents listed")

    # Partner symmetry
    for a, partners in partners_map.items():
        for b in partners:
            if b not in partners_map or a not in partners_map.get(b, set()):
                issues_partner_asym.append(f"Partner asymmetry: {a} lists {b}, but not vice versa")

    # Sibling symmetry
    siblings_map: Dict[str, Set[str]] = {}
    for n in nodes:
        siblings_map[n.get("name")] = set(n.get("siblings") or [])
    for a, sibs in siblings_map.items():
        for b in sibs:
            if a not in siblings_map.get(b, set()):
                issues_sibling_asym.append(f"Sibling asymmetry: {a} lists {b}, but not vice versa")

    # Spatial metrics
    coords_list = [n.get("coordinates") for n in nodes if isinstance(n.get("coordinates"), list) and len(n.get("coordinates")) == 4]
    min_x = min((min(c[0], c[2]) for c in coords_list), default=None)
    max_x = max((max(c[0], c[2]) for c in coords_list), default=None)
    min_y = min((min(c[1], c[3]) for c in coords_list), default=None)
    max_y = max((max(c[1], c[3]) for c in coords_list), default=None)

    # avg center y per level
    level_to_center_ys: Dict[Any, List[float]] = {}
    for n in nodes:
        center = n.get("center")
        if isinstance(center, list) and len(center) == 2:
            level_to_center_ys.setdefault(n.get("level"), []).append(float(center[1]))
    avg_center_y_per_level = {lvl: (sum(vals) / len(vals)) for lvl, vals in level_to_center_ys.items() if vals}

    # Overlapping boxes detection (naive O(n^2))
    def rect_from_coords(c: List[float]):
        x1, y1, x2, y2 = c
        left, right = min(x1, x2), max(x1, x2)
        top, bottom = min(y1, y2), max(y1, y2)
        return left, top, right, bottom

    def overlap(a: List[float], b: List[float]) -> bool:
        al, at, ar, ab = rect_from_coords(a)
        bl, bt, br, bb = rect_from_coords(b)
        return not (ar < bl or br < al or ab < bt or bb < at)

    overlapping_pairs: List[tuple] = []
    with_coords = [(n.get("name"), n.get("coordinates")) for n in nodes if isinstance(n.get("coordinates"), list) and len(n.get("coordinates")) == 4]
    for i in range(len(with_coords)):
        for j in range(i + 1, len(with_coords)):
            (na, ca), (nb, cb) = with_coords[i], with_coords[j]
            if overlap(ca, cb):
                overlapping_pairs.append((na, nb))

    return {
        "structural": {
            "generations_count": generations_count,
            "nodes_per_level": level_counts,
            "per_level_min": per_level_min,
            "per_level_max": per_level_max,
            "per_level_avg": per_level_avg,
            "root_nodes_count": root_nodes_count,
            "leaf_nodes_count": leaf_nodes_count,
        },
        "gender_and_naming": {
            "gender_distribution": dict(gender_dist),
        },
        "partnerships": {
            "partnerships_count": len(partnership_pairs),
            "avg_partners_per_node": avg_partners_per_node,
            "max_partners_for_single_node": max_partners_for_single_node,
            "divorces_count": len(divorces_pairs),
            "divorce_rate_percent": divorce_rate,
        },
        "parent_child_and_siblings": {
            "parents_completeness": {
                "zero_parents": zero_parents,
                "one_parent": one_parent,
                "two_parents": two_parents,
            },
            "children_distribution": {
                "min": min_children,
                "max": max_children,
                "avg": avg_children,
            },
            "sibling_groups_count": sibling_groups_count,
            "sibling_group_sizes": {
                "min": sibling_min,
                "max": sibling_max,
                "avg": sibling_avg,
            },
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
        },
        "consistency_checks": {
            "self_references": issues_self_ref,
            "duplicate_names": issues_duplicates,
            "contradictions": issues_contradictions,
            "partner_asymmetry": issues_partner_asym,
            "sibling_asymmetry": issues_sibling_asym,
        },
        "spatial": {
            "canvas_bounds": {
                "min_x": min_x,
                "max_x": max_x,
                "min_y": min_y,
                "max_y": max_y,
            },
            "avg_center_y_per_level": avg_center_y_per_level,
            "overlapping_boxes_count": len(overlapping_pairs),
            "overlapping_pairs": overlapping_pairs,
        },
    }


def calculate_comprehensive_score(golden_metrics: Dict[str, int], test_metrics: Dict[str, int], 
                                golden_ext: Dict[str, Any], test_ext: Dict[str, Any]) -> Dict[str, float]:
    """Calculate comprehensive score based on Option 1 Modified approach"""
    
    # Base score
    base_score = 100.0
    
    # TIER 1: Foundation Metrics (60% weight)
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
    
    # TIER 2: Relationship Metrics (25% weight)
    tier2_deductions = 0.0
    
    # Family Connections (15% of total)
    parent_diff = (abs(golden_metrics["nodes_with_mother"] - test_metrics["nodes_with_mother"]) +
                  abs(golden_metrics["nodes_with_father"] - test_metrics["nodes_with_father"]))
    tier2_deductions += parent_diff * 3
    
    # Partnerships (10% of total)
    partnership_diff = abs(golden_ext["partnerships"]["partnerships_count"] - 
                         test_ext["partnerships"]["partnerships_count"])
    tier2_deductions += partnership_diff * 2
    
    divorce_diff = abs(golden_ext["partnerships"]["divorces_count"] - 
                      test_ext["partnerships"]["divorces_count"])
    tier2_deductions += divorce_diff * 1
    
    # TIER 3: Special Attributes (10% weight)
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
    
    # Tier 4 (Quality) removed
    
    # Calculate final score
    total_deductions = (tier1_deductions * 0.63 + 
                       tier2_deductions * 0.26 + 
                       tier3_deductions * 0.11)
    
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
    print("🎯 COMPREHENSIVE SCORE BREAKDOWN")
    print("=" * 50)
    print(f"📊 FINAL SCORE: {score_data['final_score']:.1f}/100")
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
        interpretation = "❌ FAILING - Major structural failures"
    
    print(f"📈 Interpretation: {interpretation}")
    print("")
    
    print("📋 TIER BREAKDOWN:")
    print(f"   Tier 1 (Foundation 63%):     -{score_data['tier1_weighted']:.1f} pts")
    print(f"   Tier 2 (Relationships 26%):  -{score_data['tier2_weighted']:.1f} pts")
    print(f"   Tier 3 (Attributes 11%):     -{score_data['tier3_weighted']:.1f} pts")
    print(f"   Total Deductions:             -{score_data['total_deductions']:.1f} pts")
    print("")


def export_metrics_to_excel(golden: Dict[str, int], test: Dict[str, int], excel_file: str = "comparison_results.xlsx") -> None:
    if not PANDAS_AVAILABLE:
        return
    try:
        rows = []
        for key in golden.keys():
            rows.append({
                "Metric": key.replace('_', ' ').title(),
                "Golden": golden[key],
                "Test": test[key],
                "Difference (Golden - Test)": golden[key] - test[key],
            })
        df = pd.DataFrame(rows)
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='General', index=False)
            # Auto width
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
        print(f"✅ Excel report exported to: {excel_file}")
    except Exception as e:
        print(f"❌ Error exporting to Excel: {e}")


def export_extended_to_excel(excel_file: str, golden_ext: Dict[str, Any], test_ext: Dict[str, Any], 
                           golden_metrics: Dict[str, int], test_metrics: Dict[str, int], 
                           score_data: Dict[str, float]) -> None:
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
                    "Difference": (gval - tval) if isinstance(gval, (int, float)) and isinstance(tval, (int, float)) else "",
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


def main() -> None:
    golden_file = "golden.json"
    test_file = "test.json"
    
    if not os.path.exists(golden_file):
        print(f"❌ Error: {golden_file} not found")
        sys.exit(1)
    if not os.path.exists(test_file):
        print(f"❌ Error: {test_file} not found")  
        sys.exit(1)
        
    try:
        golden_data = load_json_file(golden_file)
        test_data = load_json_file(test_file)
        golden_nodes = extract_nodes(golden_data)
        test_nodes = extract_nodes(test_data)

        golden_metrics = compute_metrics(golden_nodes)
        test_metrics = compute_metrics(test_nodes)

        print_metrics("Golden JSON Metrics", golden_metrics)
        print_metrics("Test JSON Metrics", test_metrics)
        
        # Extended analytics
        golden_ext = compute_extended_metrics(golden_nodes)
        test_ext = compute_extended_metrics(test_nodes)
        
        # Calculate comprehensive score
        score_data = calculate_comprehensive_score(golden_metrics, test_metrics, golden_ext, test_ext)
        print_score_breakdown(score_data)
        
        # Export to Excel with score
        export_extended_to_excel("comparison_results.xlsx", golden_ext, test_ext, golden_metrics, test_metrics, score_data)
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()