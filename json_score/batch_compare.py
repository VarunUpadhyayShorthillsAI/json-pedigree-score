#!/usr/bin/env python3
import os
import pandas as pd
from pedigree_core import load_json_file, extract_nodes, compute_metrics, compute_extended_metrics
from pedigree_scoring import calculate_comprehensive_score

def compare_pair(golden_file, detectron_file):
    try:
        golden_data = load_json_file(golden_file)
        detectron_data = load_json_file(detectron_file)
        
        golden_nodes = extract_nodes(golden_data)
        detectron_nodes = extract_nodes(detectron_data)
        
        golden_metrics = compute_metrics(golden_nodes)
        detectron_metrics = compute_metrics(detectron_nodes)
        
        golden_ext = compute_extended_metrics(golden_nodes)
        detectron_ext = compute_extended_metrics(detectron_nodes)
        
        score_data = calculate_comprehensive_score(golden_metrics, detectron_metrics, golden_ext, detectron_ext)
        
        return score_data['final_score']
    except:
        return None

results = []

for i in range(1, 76):
    golden_file = f'golden_jsons/{i}_golden.json'
    detectron_file = f'detectron_jsons/{i}_detectron.json'
    
    if os.path.exists(golden_file) and os.path.exists(detectron_file):
        score = compare_pair(golden_file, detectron_file)
        results.append({
            'Golden File': f'{i}_golden.json',
            'Detectron File': f'{i}_detectron.json',
            'Score': score if score is not None else 'Error',
            'Image ID': ''
        })
        print(f"✅ Compared {i}_golden vs {i}_detectron: Score = {score}")

df = pd.DataFrame(results)
df.to_excel('batch_comparison_results.xlsx', index=False)
print(f"\n✅ Created batch_comparison_results.xlsx with {len(results)} comparisons")
