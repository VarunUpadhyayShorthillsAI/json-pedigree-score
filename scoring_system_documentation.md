# Pedigree JSON Scoring System Documentation

## Overview

The Pedigree JSON Scoring System is a comprehensive evaluation framework designed to assess the accuracy of pedigree (family tree) data by comparing a test JSON file against a golden (reference) JSON file. The system starts with a perfect score of **100 points** and applies deductions based on various types of discrepancies.

## How Scoring Works

### Basic Principle
- **Starting Score**: 100 points
- **Deduction-Based**: Points are subtracted when differences are found
- **Weighted Evaluation**: Different types of errors have different importance levels
- **Final Score**: Cannot go below 0 points

### Three-Tier Evaluation System

The scoring system is organized into three tiers, each with different weights reflecting their relative importance:

## 🏗️ Tier 1: Foundation (50% Weight)

This tier focuses on the basic structural integrity of the pedigree - the most critical elements that form the backbone of any family tree.

### 1. Generation Structure
- **What it measures**: How well the generation levels match between golden and test files
- **Penalty**: 
  - 1 generation difference: **-5 points**
  - 2+ generation differences: **-15 points**


### 2. Nodes per Level Distribution
- **What it measures**: Whether each generation has the correct number of people
- **Penalty**: **-2 points × generation weight** for each missing/extra person
- **Weighting Formula**: `1.0 / (1.2^level)` - Higher generations get more weight


**Generation Weight Examples:**

*For a 4-generation pedigree (levels 0-3):*
- **Level 0** (root): 32.2% weight - Most important
- **Level 1**: 26.8% weight
- **Level 2**: 22.3% weight  
- **Level 3**: 18.6% weight - Least important

*For an 8-generation pedigree (levels 0-7):*
- **Level 0** (root): 21.7% weight
- **Level 1**: 18.1% weight
- **Level 2**: 15.1% weight
- **Level 3**: 12.6% weight
- **Level 4**: 10.5% weight
- **Level 5**: 8.7% weight
- **Level 6**: 7.3% weight
- **Level 7**: 6.1% weight

**Example Calculation:**
```
4-Generation Pedigree:
Golden Level 0: 2 people    Test Level 0: 1 person
Difference: 1 person missing
Weight for Level 0: 32.2%
Penalty: 1 × 0.322 × 2 = 0.64 points

Golden Level 3: 8 people    Test Level 3: 10 people  
Difference: 2 extra people
Weight for Level 3: 18.6%
Penalty: 2 × 0.186 × 2 = 0.74 points
```

### 3. Core People Detection
- **What it measures**: Accuracy of male/female person counts
- **Penalty**: **-5 points** for each gender count discrepancy


### 4. Miscarriage Detection  
- **What it measures**: Whether pregnancy losses are correctly identified
- **Penalty**: **-2 points** for each miscarriage count difference


## 👨‍👩‍👧‍👦 Tier 2: Relationships (40% Weight)

This tier evaluates how well family relationships and connections are captured.

### 1. Parent Relationships
- **What it measures**: Parent-child relationship flags and accuracy
- **Specifically counts**:
  - **Nodes with no_parents flag**: How many nodes are marked as having no parents
- **Penalty**: **-4 points** for each incorrect parent relationship flag


### 2. Partner Relationships
- **What it measures**: Partner counts and distributions
- **Specifically counts**:
  1. **Nodes with exactly one partner**: People in monogamous relationships
  2. **Nodes with multiple partners**: People with more than one partner
- **Penalty**: **-2 points** for each partner count discrepancy


### 3. Sibling Relationships
- **What it measures**: Sibling connections and distributions
- **Specifically counts**:
  1. **Total nodes with siblings**: Overall count of nodes having siblings
  2. **Sibling distribution**: Counts of nodes with 1, 2, 3, 4, or 5+ siblings
- **Penalty**: **-1 point** for each sibling count or distribution difference


**Relationship Examples:**
```
Golden: 10 nodes with one partner, 2 with multiple partners
Test: 12 nodes with one partner, 0 with multiple partners

One partner difference: |10-12| = 2 → 2 × 2 = -4 points
Multiple partners difference: |2-0| = 2 → 2 × 2 = -4 points
Total partner penalty: -8 points

Golden: 22 nodes with siblings (10 with 1, 8 with 2, 4 with 3)
Test: 18 nodes with siblings (8 with 1, 6 with 2, 4 with 3)

Total sibling difference: |22-18| = 4 → 4 × 1 = -4 points
Distribution differences: (|10-8| + |8-6| + |4-4|) = 4 → 4 × 1 = -4 points
Total sibling penalty: -8 points
```

**Partnership Examples:**
```
Golden partnerships_count: 8, divorces_count: 2
Test partnerships_count: 6, divorces_count: 3

Partnership difference: |8-6| = 2 → 2 × 2 = -4 points
Divorce difference: |2-3| = 1 → 1 × 1 = -1 point
Total penalty: -5 points
```

## 🏥 Tier 3: Attributes (10% Weight)

This tier covers additional characteristics and medical information that enhance pedigree utility.

### 1. Disease Patterns
- **What it measures**: Medical conditions, genetic markers, and inheritance patterns
- **Penalty**: **-1 point** for each disease pattern difference
- **Examples**: Cancer markers, genetic conditions, shading patterns

### 2. Important Symbols
- **What it measures**: Critical life status and family situation markers
- **Penalty**: **-2 points** for each important symbol difference
- **Examples**: Deceased status, adopted_in/adopted_out, pregnancy status

### 3. Twin Relationships
- **What it measures**: Twin relationships and their types
- **Penalty**: **-1 point** for each twin relationship difference
- **Types**: DZ twins (dizygotic/fraternal), MZ twins (monozygotic/identical)

## Score Calculation Formula

```
total_deductions = (tier1_deductions × 0.50) + 
                  (tier2_deductions × 0.40) + 
                  (tier3_deductions × 0.10)

final_score = max(0.0, 100 - total_deductions)
```

### Weight Distribution
- **Tier 1 (Foundation)**: 50% - Most important structural elements
- **Tier 2 (Relationships)**: 40% - Family connections and partnerships  
- **Tier 3 (Attributes)**: 10% - Additional characteristics and medical data

## Score Interpretation Guide

| Score Range | Grade | Description | Typical Issues |
|-------------|-------|-------------|----------------|
| **90-100** | 🟢 EXCELLENT | Minor issues only | Small attribute differences |
| **80-89** | 🟡 GOOD | Some relationship/attribute errors | Missing partnerships, minor medical data |
| **70-79** | 🟠 ACCEPTABLE | Foundation mostly correct | Some structural issues, relationship gaps |
| **60-69** | 🔴 POOR | Significant structural problems | Generation errors, major relationship issues |
| **0-59** | ❌ FAILING | Major structural failures | Fundamental structural breakdown |

## How to Use This System

### For Beginners
1. **Start with Tier 1**: Ensure basic structure is correct (generations, people counts)
2. **Check Tier 2**: Verify family relationships are properly connected
3. **Review Tier 3**: Add medical and attribute details

### For Intermediate Users
1. **Understand Weighting**: Focus effort on higher-weighted tiers first
2. **Generation Weighting**: Pay extra attention to earlier generations
3. **Error Prioritization**: Fix high-penalty errors before low-penalty ones

### Common Improvement Strategies
- **Score 60-79**: Focus on Tier 1 foundation issues first
- **Score 80-89**: Review Tier 2 relationship connections  
- **Score 90+**: Fine-tune Tier 3 attributes and medical data

## Examples of Point Deductions

### Foundation Issues (High Impact)
- Missing a person in generation 0: ~1.0 points (2 × 0.50 weighting)
- Missing a person in generation 1: ~0.8 points (due to generation weighting)
- Wrong number of generations: 5-15 points (× 0.50 weighting)
- Incorrect gender count: 5 points (× 0.50 weighting)

### Relationship Issues (Medium Impact)  
- Missing parent-child connection: ~2.0 points (4 × 0.40 weighting)
- Partnership count difference: ~1.6 points (4 × 0.40 weighting)
- Sibling count difference: ~0.4 points (1 × 0.40 weighting)

### Attribute Issues (Lower Impact)
- Missing disease marker: ~0.1 points (1 × 0.10 weighting)
- Wrong deceased status: ~0.2 points (2 × 0.10 weighting)

## Best Practices

1. **Validate Structure First**: Ensure correct generations and person counts
2. **Map Relationships Carefully**: Double-check parent-child and partnership connections
3. **Include Medical History**: Add disease patterns and important life events
4. **Test Iteratively**: Use the scoring system to identify and fix issues progressively

