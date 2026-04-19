import json
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Set

def clean_name(name: str) -> str:
    """
    Cleans ingredient name from extra words
    """
    # Remove "Большой мешок" from start
    name = re.sub(r'^Большой мешок\s+', '', name)
    
    # Remove "базового" if present
    name = re.sub(r'^базового\s+', '', name)
    
    # Remove ingredient type in different cases
    name = re.sub(r'^(солод|солода|хмель|хмеля|дрожжи|дрожжей)\s+', '', name, flags=re.IGNORECASE)
    
    # Remove quality at the end
    name = re.sub(r'\s+(высокого|среднего|низкого)\s+качества$', '', name)
    
    return name.strip()

def extract_quality(name: str) -> str:
    """
    Extracts quality from name
    """
    quality_match = re.search(r'(высокого|среднего|низкого)\s+качества', name)
    return quality_match.group(1) if quality_match else 'standard'

def compare_values(val1, val2, tolerance: float = 0.01) -> bool:
    """
    Compare two values with tolerance for floats
    """
    if isinstance(val1, float) and isinstance(val2, float):
        return abs(val1 - val2) < tolerance
    return val1 == val2

def compare_dicts(dict1: Dict, dict2: Dict, dict_name: str) -> Tuple[bool, List[str]]:
    """
    Compare two dictionaries and return (match, differences)
    """
    all_keys = set(dict1.keys()) | set(dict2.keys())
    differences = []
    
    for key in all_keys:
        val1 = dict1.get(key, 0)
        val2 = dict2.get(key, 0)
        
        if not compare_values(val1, val2):
            differences.append(f"    {key}: {val1} vs {val2}")
    
    return len(differences) == 0, differences

def simplify_ingredients(input_file: str, output_file: str = "ingredients_simplified.json"):
    """
    Simplifies ingredients JSON:
    - Removes extra words from names
    - Removes Rate field from parameters
    - Groups all variations of the same component
    - Checks that all variations have same characteristics
    """
    
    # Read source JSON
    with open(input_file, 'r', encoding='utf-8') as f:
        ingredients = json.load(f)
    
    print(f"📦 Loaded ingredients: {len(ingredients)}")
    print("=" * 60)
    
    # Group by base name and type
    groups = defaultdict(list)
    for item in ingredients:
        base_name = clean_name(item['Name'])
        quality = extract_quality(item['Name'])
        
        # Remove Rate from parameters
        clean_params = {k: v for k, v in item['Parameters'].items() if k != 'Rate'}
        
        group_key = (base_name, item['Type'])
        groups[group_key].append({
            'original_name': item['Name'],
            'quality': quality,
            'perfect_temp': item['PerfectTemp'],
            'styles': item['Styles'],
            'params': clean_params
        })
    
    print(f"\n🔍 Unique components found: {len(groups)}")
    print("-" * 60)
    
    simplified = []
    has_inconsistencies = False
    
    # Process each group
    for (base_name, ing_type), variants in sorted(groups.items()):
        print(f"\n📦 Component: {base_name} ({ing_type})")
        print(f"   Variants: {len(variants)}")
        
        if len(variants) == 1:
            # If only one variant, just add it
            var = variants[0]
            simplified.append({
                'Name': base_name,
                'Type': ing_type,
                'PerfectTemp': var['perfect_temp'],
                'Styles': var['styles'],
                'Parameters': var['params']
            })
            print(f"   ✅ Single variant")
            continue
        
        # Check if all variants have same characteristics
        reference = variants[0]
        all_match = True
        inconsistencies = []
        
        for i, var in enumerate(variants[1:], 2):
            var_differences = []
            
            # Check temperature
            if var['perfect_temp'] != reference['perfect_temp']:
                all_match = False
                var_differences.append(f"      Temperature: {reference['perfect_temp']}°C vs {var['perfect_temp']}°C")
            
            # Check styles
            styles_match, style_diffs = compare_dicts(reference['styles'], var['styles'], "Styles")
            if not styles_match:
                all_match = False
                var_differences.append("      Style differences:")
                var_differences.extend(style_diffs)
            
            # Check parameters
            params_match, param_diffs = compare_dicts(reference['params'], var['params'], "Parameters")
            if not params_match:
                all_match = False
                var_differences.append("      Parameter differences:")
                var_differences.extend(param_diffs)
            
            if var_differences:
                inconsistencies.append(f"\n   Variant {i} ({var['quality']} quality):")
                inconsistencies.extend(var_differences)
        
        if all_match:
            # All variants identical - take any (first)
            simplified.append({
                'Name': base_name,
                'Type': ing_type,
                'PerfectTemp': reference['perfect_temp'],
                'Styles': reference['styles'],
                'Parameters': reference['params']
            })
            print(f"   ✅ All {len(variants)} variants are identical")
            print(f"      Qualities: {', '.join(v['quality'] for v in variants)}")
        else:
            # Differences found - show warning
            has_inconsistencies = True
            print(f"   ⚠️  WARNING! Differences detected between variants:")
            
            # Show all variants with their characteristics
            for i, var in enumerate(variants, 1):
                print(f"\n      Variant {i} ({var['quality']} quality):")
                print(f"         Original: {var['original_name']}")
                print(f"         Temperature: {var['perfect_temp']}°C")
                print(f"         Styles: {var['styles']}")
                print(f"         Parameters: {var['params']}")
            
            # Show detailed differences
            print(f"\n      Detailed differences:")
            for diff in inconsistencies:
                print(diff)
            
            # Still add all variants separately
            print(f"\n      ➕ Adding all variants separately")
            for var in variants:
                simplified.append({
                    'Name': f"{base_name} ({var['quality']})",
                    'Type': ing_type,
                    'PerfectTemp': var['perfect_temp'],
                    'Styles': var['styles'],
                    'Parameters': var['params']
                })
    
    # Save result
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(simplified, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(f"\n✅ Simplified JSON saved to: {output_file}")
    print(f"📊 Final statistics:")
    print(f"   Original ingredients: {len(ingredients)}")
    print(f"   Simplified ingredients: {len(simplified)}")
    
    if has_inconsistencies:
        print("\n⚠️  WARNING! Components with different characteristics found:")
        print("   They were saved as separate ingredients with quality indicators")
        print("   Check the original file for data consistency")

def main():
    print("=" * 60)
    print("🛠️  INGREDIENT JSON SIMPLIFIER")
    print("=" * 60)
    
    input_file = "ingredients.json"
    output_file = "ingredients_simplified.json"
    
    try:
        simplify_ingredients(input_file, output_file)
        
        print("\n" + "=" * 60)
        print("✅ DONE!")
        print("=" * 60)
        
    except FileNotFoundError:
        print(f"❌ File {input_file} not found!")
    except json.JSONDecodeError:
        print(f"❌ JSON format error!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()