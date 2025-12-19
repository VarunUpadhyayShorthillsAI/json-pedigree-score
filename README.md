# JSON Pedigree Score

A comprehensive scoring system for evaluating pedigree (family tree) JSON data by comparing model-generated outputs against ground truth references.

## Overview

This project provides a sophisticated scoring mechanism to assess the accuracy of pedigree data extraction models. It compares two JSON files (golden/reference vs test/detectron output) and generates detailed scores based on structural accuracy, relationship correctness, and medical attributes.

## Features

- **Batch Comparison**: Compare multiple JSON pairs at once (up to 75 pairs)
- **Comprehensive Scoring**: Three-tier weighted scoring system (100-point scale)
  - **Tier 1 (50%)**: Foundation metrics (structure, generations, node detection)
  - **Tier 2 (40%)**: Relationship metrics (parents, partners, siblings)
  - **Tier 3 (10%)**: Attribute metrics (diseases, symbols, twins)
- **Flexible JSON Format**: Handles both `original_json` and `updated_json` structures
- **Excel Export**: Detailed results with scores for each comparison
- **Generation Weighting**: Higher penalty for errors in earlier generations

## Project Structure

```
json-pedigree-score/
├── json_score/
│   ├── pedigree_main.py              # Single comparison script
│   ├── batch_compare.py              # Batch comparison script (NEW)
│   ├── pedigree_core.py              # Core functions (JSON loading, metrics)
│   ├── pedigree_scoring.py           # Scoring calculations
│   ├── pedigree_export.py            # Excel export functionality
│   ├── golden_jsons/                 # Ground truth JSON files (75 files)
│   ├── detectron_jsons/              # Model output JSON files (75 files)
│   ├── batch_comparison_results.xlsx # Batch results output
│   └── requirements.txt              # Python dependencies
└── training_Scripts/
    ├── dataset_download.py
    ├── train.py
    └── evaluator.py
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/VarunUpadhyayShorthillsAI/json-pedigree-score.git
cd json-pedigree-score/json_score
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Requirements
- Python 3.9+
- pandas >= 2.0.0
- openpyxl >= 3.1.0

## Usage

### Batch Comparison (Compare Multiple Pairs)

Compare all JSON pairs in the `golden_jsons/` and `detectron_jsons/` folders:

```bash
cd json_score
python3 batch_compare.py
```

**Output**: `batch_comparison_results.xlsx` containing:
- Golden File name
- Detectron File name
- Score (0-100)
- Image ID (empty, for manual filling)

### Single Comparison

Compare two specific JSON files:

1. Place your files:
   - `golden.json` - Ground truth/reference file
   - `test.json` - Model output/test file

2. Run comparison:
```bash
python3 pedigree_main.py
```

**Output**: 
- Console output with metrics and score
- `comparison_results.xlsx` with detailed breakdowns

## JSON File Format

The system accepts JSON files in the following formats:

### Format 1: Nested with original_json
```json
{
  "original_json": {
    "json": [
      {
        "name": "1",
        "sex": "M",
        "level": 0,
        "partners": ["2"],
        ...
      }
    ]
  }
}
```

### Format 2: Nested with updated_json
```json
{
  "updated_json": {
    "json": [
      {
        "name": "1",
        "sex": "F",
        "level": 0,
        ...
      }
    ]
  }
}
```

### Format 3: Direct array
```json
{
  "json": [
    {
      "name": "1",
      ...
    }
  ]
}
```

## Scoring System

### Score Interpretation
- **90-100**: 🟢 EXCELLENT - Minor issues only
- **80-89**: 🟡 GOOD - Some relationship/attribute errors
- **70-79**: 🟠 ACCEPTABLE - Foundation mostly correct
- **60-69**: 🔴 POOR - Significant structural problems
- **<60**: ❌ FAILING - Major structural failures

### What Gets Compared

#### Tier 1: Foundation (50% weight)
- Number of generations
- Nodes per generation level (with generation weighting)
- Gender distribution (Male/Female/Miscarriage/Unknown)
- Total node count

#### Tier 2: Relationships (40% weight)
- Parent relationships (father/mother)
- Partnership relationships (single/multiple partners)
- Sibling relationships and distributions
- Divorce relationships

#### Tier 3: Attributes (10% weight)
- Disease patterns (28 different shading types)
- Status symbols (Deceased, Adopted, Patient, Carrier)
- Twin relationships (MZ/DZ twins)

## Current Test Results

**75 JSON pairs compared** (as of latest batch):
- **Average Score**: 87.58/100
- **Perfect Scores (100)**: 24 files
- **Excellent (90-99)**: 15 files
- **Good (80-89)**: 20 files
- **Acceptable (70-79)**: 10 files
- **Poor/Failing (<70)**: 6 files

## File Naming Convention

For batch processing, files must follow this naming pattern:
- Golden files: `1_golden.json`, `2_golden.json`, ..., `75_golden.json`
- Detectron files: `1_detectron.json`, `2_detectron.json`, ..., `75_detectron.json`

## Adding Your Own JSON Files

1. **For batch comparison**:
   - Place golden files in `json_score/golden_jsons/`
   - Place detectron files in `json_score/detectron_jsons/`
   - Use the naming convention: `{number}_golden.json` and `{number}_detectron.json`
   - Run `python3 batch_compare.py`

2. **For single comparison**:
   - Name your files `golden.json` and `test.json`
   - Place them in the `json_score/` directory
   - Run `python3 pedigree_main.py`

## Key Metrics Tracked

### Structural Metrics
- Generations count
- Nodes per level distribution
- Root and leaf nodes
- Generation structure accuracy

### Relationship Metrics
- Partnerships (count, symmetry)
- Divorces
- Parent completeness (zero/one/two parents)
- Sibling groups and distributions

### Medical/Attribute Metrics
- 28 disease pattern types (e.g., CIRCLE_FILLED, SQUARE_CHECKERED)
- Important symbols (Deceased, Adopted_in/out, Carrier, Patient)
- Twin relationships (Monozygotic, Dizygotic)

### Quality Checks
- Self-references detection
- Duplicate names
- Partner/sibling asymmetry
- Contradictions (e.g., top_level with parents)

## Documentation

For detailed scoring methodology, see:
- `json_score/scoring_system_documentation.md` - Complete scoring breakdown
- `json_score/scoring_system_chart.html` - Visual scoring guide

## Contributing

This is a research/evaluation project. To contribute:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is maintained by Varun Upadhyay for Shorthills AI.

## Contact

For questions or issues, please open an issue on the GitHub repository.

---

**Last Updated**: December 2025  
**Version**: 2.0 (Batch Comparison System)

