import json
import itertools
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict
import os
from datetime import datetime

class Ingredient:
    def __init__(self, name: str, type: str, perfect_temp: int, style: Dict[str, float], params: Dict[str, float]):
        self.name = name
        self.type = type
        self.perfect_temp = perfect_temp
        self.style = style
        self.params = params
    
    def __repr__(self):
        return f"Ingredient(name='{self.name}', type='{self.type}')"

class CraftCalculator:
    # Style translation dictionary (UPDATED with Stout)
    STYLE_TRANSLATION = {
        'Ale_1': 'Bristford Ale',
        'Hefeweizen_1': 'Hallbruck Hellas',
        'AmericanIpa_1': 'Cascadear IPA',
        'Stout_1': 'Stout'
    }
    
    # Reverse dictionary for user input lookup
    STYLE_REVERSE = {v.lower(): k for k, v in STYLE_TRANSLATION.items()}
    
    # List of available styles for display
    AVAILABLE_STYLES = list(STYLE_TRANSLATION.values())
    
    # Significant parameters
    VALID_PARAMS = ['Refreshment', 'Heaviness', 'Lightness', 'Acidity', 'Sweetness']
    
    def __init__(self, json_file_path: str):
        """
        Initialize calculator with prepared JSON file
        """
        self.ingredients = self.load_ingredients_from_json(json_file_path)
        
        # Split ingredients by type
        self.malts = [i for i in self.ingredients if i.type == "Malts"]
        self.hops = [i for i in self.ingredients if i.type == "Hops"]
        self.yeast = [i for i in self.ingredients if i.type == "Yeast"]
        
        print(f"📊 Loaded ingredients: {len(self.ingredients)}")
        print(f"  🌾 Malts: {len(self.malts)}")
        print(f"  🌿 Hops: {len(self.hops)}")
        print(f"  🧪 Yeast: {len(self.yeast)}")
    
    def load_ingredients_from_json(self, file_path: str) -> List[Ingredient]:
        """
        Load ingredients from prepared JSON file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            ingredients = []
            for item in data:
                # Check that all required fields exist
                if 'Name' not in item or 'Type' not in item or 'PerfectTemp' not in item:
                    print(f"⚠️ Skipped ingredient: missing required fields")
                    continue
                
                ingredient = Ingredient(
                    name=item['Name'],
                    type=item['Type'],
                    perfect_temp=item['PerfectTemp'],
                    style=item.get('Styles', {}),
                    params=item.get('Parameters', {})
                )
                ingredients.append(ingredient)
            
            return ingredients
            
        except FileNotFoundError:
            raise Exception(f"❌ File {file_path} not found")
        except json.JSONDecodeError as e:
            raise Exception(f"❌ JSON format error: {e}")
    
    def translate_style(self, style_code: str, to_user: bool = True) -> str:
        """
        Translate style between code and user-friendly name
        to_user=True: code -> name
        to_user=False: name -> code
        """
        if to_user:
            return self.STYLE_TRANSLATION.get(style_code, style_code)
        else:
            return self.STYLE_REVERSE.get(style_code.lower(), style_code)
    
    def parse_user_input(self, user_input: str) -> Tuple[Optional[str], Optional[List[str]]]:
        """
        Parse user input into style and parameters
        Supports multi-word style names
        """
        user_input = user_input.strip()
        user_input_lower = user_input.lower()
        
        # Sort styles by length for correct matching
        sorted_styles = sorted(self.STYLE_REVERSE.keys(), key=len, reverse=True)
        
        for style_lower in sorted_styles:
            if user_input_lower.startswith(style_lower):
                # Found style
                style_display = next(v for k, v in self.STYLE_TRANSLATION.items() 
                                   if v.lower() == style_lower)
                
                # Remaining string is parameters
                remaining = user_input[len(style_lower):].strip()
                params = remaining.split() if remaining else None
                
                return style_display, params
        
        return None, None
    
    def calculate_result(self, malt: Ingredient, hop: Ingredient, yeast: Ingredient) -> Dict:
        """
        Calculate result of combining three ingredients
        """
        # Calculate style scores
        style_scores = {}
        for ing in [malt, hop, yeast]:
            for style, weight in ing.style.items():
                style_scores[style] = style_scores.get(style, 0) + weight
        
        # If no styles, return error
        if not style_scores:
            return {
                'error': 'No style data',
                'malt': malt.name,
                'hop': hop.name,
                'yeast': yeast.name
            }
        
        # Find maximum value
        sorted_styles = sorted(style_scores.items(), key=lambda x: x[1], reverse=True)
        max_score = sorted_styles[0][1]
        
        # Check for tie
        max_count = sum(1 for _, score in style_scores.items() if abs(score - max_score) < 0.01)
        is_tie = max_count >= 2
        
        if is_tie:
            result_style = sorted_styles[0][0]
            result_style_display = f"{self.translate_style(result_style)}"
        else:
            result_style = sorted_styles[0][0]
            result_style_display = self.translate_style(result_style)
        
        # Calculate parameters
        param_scores = {}
        for ing in [malt, hop, yeast]:
            for param, value in ing.params.items():
                if param in self.VALID_PARAMS:
                    param_scores[param] = param_scores.get(param, 0) + value
        
        active_params = [param for param, value in param_scores.items() if value >= 10]
        
        # Format style details for display
        style_details = []
        for style_code, score in style_scores.items():
            style_name = self.translate_style(style_code)
            style_details.append(f"{style_name}: {score:.2f}")
        
        return {
            'malt': malt.name,
            'hop': hop.name,
            'yeast': yeast.name,
            'style': result_style,
            'style_display': result_style_display,
            'style_scores': style_scores,
            'style_details': style_details,
            'is_tie': is_tie,
            'params': param_scores,
            'active_params': active_params,
            'perfect_temps': {
                'malt': malt.perfect_temp,
                'hop': hop.perfect_temp,
                'yeast': yeast.perfect_temp
            }
        }
    
    def find_combinations(self, target_style_display: str, target_params: List[str] = None, 
                         exclude_ties: bool = True) -> List[Dict]:
        """
        Find all combinations for given style and parameters
        exclude_ties: if True, excludes tie combinations
        """
        target_style_code = self.translate_style(target_style_display, to_user=False)
        results = []
        
        total_combinations = len(self.malts) * len(self.hops) * len(self.yeast)
        print(f"  🔄 Checking {total_combinations} combinations...")
        
        for malt in self.malts:
            for hop in self.hops:
                for yeast in self.yeast:
                    result = self.calculate_result(malt, hop, yeast)
                    
                    if 'error' in result:
                        continue
                    
                    # Skip ties if needed
                    if exclude_ties and result['is_tie']:
                        continue
                    
                    if result['style'] != target_style_code:
                        continue
                    
                    if target_params:
                        formatted_params = [p.capitalize() for p in target_params]
                        if not all(param in result['active_params'] for param in formatted_params):
                            continue
                    
                    results.append(result)
        
        return results
    
    def find_minimal_coverage(self, target_style_display: str, exclude_ties: bool = True) -> List[List[Dict]]:
        """
        Find minimal set of combinations covering all possible properties
        exclude_ties: if True, excludes tie combinations
        """
        target_style_code = self.translate_style(target_style_display, to_user=False)
        
        # Find all combinations for this style (excluding ties)
        all_combinations = []
        for malt in self.malts:
            for hop in self.hops:
                for yeast in self.yeast:
                    result = self.calculate_result(malt, hop, yeast)
                    if 'error' not in result and result['style'] == target_style_code:
                        if exclude_ties and result['is_tie']:
                            continue
                        all_combinations.append(result)
        
        if not all_combinations:
            return []
        
        # Get all possible properties
        all_params = set(self.VALID_PARAMS)
        
        # For each combination, get set of active properties
        combo_sets = []
        for combo in all_combinations:
            params_set = set(combo['active_params'])
            if params_set:  # Only combinations with at least one property
                combo_sets.append((combo, params_set))
        
        if not combo_sets:
            return []
        
        # Use greedy algorithm to find coverage
        uncovered = set(all_params)
        selected_combos = []
        selected_indices = set()
        
        while uncovered:
            best_combo = None
            best_coverage = set()
            best_idx = -1
            
            for i, (combo, params_set) in enumerate(combo_sets):
                if i in selected_indices:
                    continue
                
                coverage = params_set & uncovered
                if len(coverage) > len(best_coverage):
                    best_coverage = coverage
                    best_combo = combo
                    best_idx = i
            
            if best_combo is None:
                break
            
            selected_combos.append(best_combo)
            selected_indices.add(best_idx)
            uncovered -= best_coverage
        
        return [selected_combos]
    
    def find_all_minimal_coverages(self, target_style_display: str, exclude_ties: bool = True) -> List[List[Dict]]:
        """
        Find ALL possible minimal coverage sets (more accurate algorithm)
        exclude_ties: if True, excludes tie combinations
        """
        target_style_code = self.translate_style(target_style_display, to_user=False)
        
        # Find all combinations (excluding ties)
        all_combinations = []
        for malt in self.malts:
            for hop in self.hops:
                for yeast in self.yeast:
                    result = self.calculate_result(malt, hop, yeast)
                    if 'error' not in result and result['style'] == target_style_code:
                        if exclude_ties and result['is_tie']:
                            continue
                        all_combinations.append(result)
        
        if not all_combinations:
            return []
        
        # Create dictionary combo -> property set
        combo_dict = {}
        for combo in all_combinations:
            params_set = frozenset(combo['active_params'])
            if params_set:
                key = (combo['malt'], combo['hop'], combo['yeast'])
                combo_dict[key] = {
                    'combo': combo,
                    'params': params_set
                }
        
        all_params = set(self.VALID_PARAMS)
        
        # Recursive function to find all minimal coverings
        def find_coverings(remaining_params: Set[str], 
                          available_combos: Dict, 
                          current_solution: List,
                          best_solutions: List,
                          current_length: int = 0):
            
            # If we found a covering
            if not remaining_params:
                # If this is first solution or same length
                if not best_solutions or current_length == len(best_solutions[0]):
                    best_solutions.append(current_solution.copy())
                elif current_length < len(best_solutions[0]):
                    # Found better solution
                    best_solutions.clear()
                    best_solutions.append(current_solution.copy())
                return
            
            # Prune if we already exceed best solution length
            if best_solutions and current_length >= len(best_solutions[0]):
                return
            
            # Try adding each combination
            for key, data in list(available_combos.items()):
                new_params = data['params'] & remaining_params
                if not new_params:
                    continue
                
                # Create new sets for recursion
                new_remaining = remaining_params - new_params
                new_available = {k: v for k, v in available_combos.items() if k != key}
                
                current_solution.append(data['combo'])
                find_coverings(new_remaining, new_available, current_solution, 
                             best_solutions, current_length + 1)
                current_solution.pop()
        
        # Start search
        solutions = []
        find_coverings(all_params, combo_dict, [], solutions)
        
        # Remove duplicates (solutions differing only in order)
        unique_solutions = []
        seen = set()
        
        for sol in solutions:
            # Sort for comparison
            sorted_sol = sorted([(c['malt'], c['hop'], c['yeast']) for c in sol])
            key = tuple(sorted_sol)
            if key not in seen:
                seen.add(key)
                unique_solutions.append(sol)
        
        return unique_solutions
    
    def save_coverage_to_file(self, target_style: str, solutions: List[List[Dict]], filename: str = None):
        """
        Save coverage results to a human-readable text file
        """
        if not filename:
            # Create filename from style name
            safe_style = target_style.replace(' ', '_').lower()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"coverage_{safe_style}_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # Write header
                f.write("=" * 80 + "\n")
                f.write(f"🍺 CRAFTING CALCULATOR - COVERAGE REPORT\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"🎯 Style: {target_style}\n")
                f.write(f"📊 Total variants found: {len(solutions)}\n")
                f.write(f"📦 Combinations per variant: {len(solutions[0]) if solutions else 0}\n\n")
                
                for i, solution in enumerate(solutions, 1):
                    f.write("=" * 80 + "\n")
                    f.write(f"📦 VARIANT #{i}\n")
                    f.write("=" * 80 + "\n\n")
                    
                    # Collect all properties covered by this set
                    covered_params = set()
                    for combo in solution:
                        covered_params.update(combo['active_params'])
                    
                    f.write(f"   Covered properties: {', '.join(sorted(covered_params))}\n\n")
                    
                    for j, combo in enumerate(solution, 1):
                        f.write(f"   🍺 COMBINATION {j}:\n")
                        f.write(f"      {'=' * 40}\n")
                        f.write(f"      🌾 MALT:    {combo['malt']}\n")
                        f.write(f"      🌿 HOP:     {combo['hop']}\n")
                        f.write(f"      🧪 YEAST:   {combo['yeast']}\n")
                        f.write(f"      {'-' * 40}\n")
                        f.write(f"      ⚡ ACTIVE PROPERTIES:\n")
                        if combo['active_params']:
                            for param in combo['active_params']:
                                f.write(f"         • {param}\n")
                        else:
                            f.write(f"         • None\n")
                        
                        f.write(f"\n      📊 PARAMETER VALUES:\n")
                        # Sort parameters by value descending
                        sorted_params = sorted(combo['params'].items(), key=lambda x: x[1], reverse=True)
                        for param, value in sorted_params:
                            status = "✓" if value >= 10 else "✗"
                            bar = "█" * int(value) + "░" * (10 - int(value))
                            f.write(f"         {param:12}: {value:5.1f} {status} {bar}\n")
                        
                        f.write(f"\n      🌡️  TEMPERATURES:\n")
                        f.write(f"         Malt:  {combo['perfect_temps']['malt']}°C\n")
                        f.write(f"         Hop:   {combo['perfect_temps']['hop']}°C\n")
                        f.write(f"         Yeast: {combo['perfect_temps']['yeast']}°C\n")
                        
                        f.write(f"\n      📊 STYLE DISTRIBUTION:\n")
                        for detail in combo['style_details']:
                            f.write(f"         • {detail}\n")
                        
                        f.write(f"\n")
                    
                    f.write("\n")
                
                # Write footer
                f.write("=" * 80 + "\n")
                f.write("🏁 END OF REPORT\n")
                f.write("=" * 80 + "\n")
            
            print(f"\n💾 Report saved to: {filename}")
            return filename
            
        except Exception as e:
            print(f"\n❌ Error saving file: {e}")
            return None
    
    def print_minimal_coverage(self, target_style: str, save_to_file: bool = True):
        """
        Print minimal coverage sets for a style and optionally save to file
        (excluding tie combinations)
        """
        print(f"\n🔍 SEARCHING FOR MINIMAL COVERAGE SET FOR {target_style}")
        print("=" * 80)
        
        # Use accurate algorithm, excluding ties
        solutions = self.find_all_minimal_coverages(target_style, exclude_ties=True)
        
        if not solutions:
            print("❌ No combinations found covering all properties")
            print("   (maybe all combinations have ties or no suitable ones)")
            return
        
        print(f"\n✅ Found {len(solutions)} minimal coverage variants")
        print(f"   Each set contains {len(solutions[0])} combinations")
        print("=" * 80)
        
        for i, solution in enumerate(solutions, 1):
            print(f"\n📦 VARIANT #{i}")
            print("-" * 60)
            
            # Collect all properties covered by this set
            covered_params = set()
            for combo in solution:
                covered_params.update(combo['active_params'])
            
            print(f"   Covered properties: {', '.join(sorted(covered_params))}")
            print()
            
            for j, combo in enumerate(solution, 1):
                print(f"   🍺 Combination {j}:")
                print(f"      🌾 {combo['malt']}")
                print(f"      🌿 {combo['hop']}")
                print(f"      🧪 {combo['yeast']}")
                print(f"      ⚡ Properties: {', '.join(combo['active_params'])}")
                print()
        
        # Save to file if requested
        if save_to_file:
            self.save_coverage_to_file(target_style, solutions)
    
    def print_combinations(self, target_style: str, target_params: List[str] = None):
        """
        Print found combinations (excluding ties)
        """
        combinations = self.find_combinations(target_style, target_params, exclude_ties=True)
        
        if not combinations:
            params_str = f" with parameters {target_params}" if target_params else ""
            print(f"\n❌ No combinations found for {target_style}{params_str}")
            print("   (maybe all combinations have ties)")
            return
        
        print(f"\n✅ Found {len(combinations)} combinations for {target_style}")
        if target_params:
            print(f"📌 With parameters: {', '.join(target_params)}")
        print("=" * 80)
        
        for i, combo in enumerate(combinations, 1):
            print(f"\n🎯 --- Combination #{i} ---")
            print(f"  🌾 Malts: {combo['malt']}")
            print(f"  🌿 Hops: {combo['hop']}")
            print(f"  🧪 Yeast: {combo['yeast']}")
            print(f"  🍺 Result: {combo['style_display']}")
            print(f"  📊 Style distribution: {', '.join(combo['style_details'])}")
            print(f"  ⚡ Active properties: {', '.join(combo['active_params']) if combo['active_params'] else 'none'}")
            print(f"  🌡️  Temperatures: Malt:{combo['perfect_temps']['malt']}°C, Hop:{combo['perfect_temps']['hop']}°C, Yeast:{combo['perfect_temps']['yeast']}°C")
            print(f"  📊 Parameter values:")
            
            # Sort parameters by value descending
            sorted_params = sorted(combo['params'].items(), key=lambda x: x[1], reverse=True)
            for param, value in sorted_params:
                status = "✅" if value >= 10 else "❌"
                bar = "█" * int(value) + "░" * (10 - int(value))
                print(f"     {param:12}: {value:5.1f} {status} {bar}")
    
    def find_tie_combinations(self) -> List[Dict]:
        """
        Find all combinations with ties
        """
        results = []
        
        for malt in self.malts:
            for hop in self.hops:
                for yeast in self.yeast:
                    result = self.calculate_result(malt, hop, yeast)
                    if 'error' not in result and result['is_tie']:
                        results.append(result)
        
        return results
    
    def print_tie_combinations(self):
        """
        Print all tie combinations
        """
        combinations = self.find_tie_combinations()
        
        if not combinations:
            print("\n✅ No tie combinations found")
            return
        
        print(f"\n⚠️ FOUND {len(combinations)} TIE COMBINATIONS")
        print("=" * 80)
        
        for i, combo in enumerate(combinations, 1):
            print(f"\n⚠️ --- Tie #{i} ---")
            print(f"  🌾 Malts: {combo['malt']}")
            print(f"  🌿 Hops: {combo['hop']}")
            print(f"  🧪 Yeast: {combo['yeast']}")
            print(f"  📊 Style distribution: {', '.join(combo['style_details'])}")
            print(f"  ⚡ Active properties: {', '.join(combo['active_params']) if combo['active_params'] else 'none'}")

def print_help():
    """Print help information"""
    print("\n" + "="*60)
    print("📖 HELP")
    print("="*60)
    print("  🍺 STYLES:")
    print("     • Bristford Ale")
    print("     • Hallbruck Hellas")
    print("     • Cascadear IPA")
    print("     • Stout")
    print("\n  ⚡ PARAMETERS:")
    print("     • Refreshment, Heaviness, Lightness, Acidity, Sweetness")
    print("\n  📝 EXAMPLES:")
    print("     • Bristford Ale")
    print("     • Stout lightness heaviness")
    print("     • cascadear ipa sweetness")
    print("\n  🎯 SPECIAL COMMANDS:")
    print("     • cover <style> - find minimal set covering all properties")
    print("     • ties - show all tie combinations")
    print("     • stats - show statistics")
    print("     • help - show this help")
    print("     • exit - exit program")
    print("\n  ℹ️  NOTE:")
    print("     • Cover results are automatically saved to a text file")
    print("     • Tie combinations are excluded from regular search")
    print("="*60)

def main():
    """Main function with continuous input loop"""
    print("="*60)
    print("🍺 CRAFTING CALCULATOR (v 2.3)")
    print("="*60)
    
    # Specify path to prepared JSON file
    json_file = "ingredients.json"
    
    try:
        calculator = CraftCalculator(json_file)
        print_help()
        
        while True:
            try:
                print("\n" + ">"*40)
                user_input = input("🔍 Enter query: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() == 'exit':
                    print("👋 Goodbye!")
                    break
                
                elif user_input.lower() == 'help':
                    print_help()
                    continue
                
                elif user_input.lower() == 'stats':
                    print(f"\n📊 Statistics:")
                    print(f"  Total ingredients: {len(calculator.ingredients)}")
                    print(f"  Malts: {len(calculator.malts)}")
                    print(f"  Hops: {len(calculator.hops)}")
                    print(f"  Yeast: {len(calculator.yeast)}")
                    continue
                
                elif user_input.lower() == 'ties':
                    calculator.print_tie_combinations()
                    continue
                
                # Handle cover command
                if user_input.lower().startswith('cover '):
                    style = user_input[6:].strip()
                    if style:
                        calculator.print_minimal_coverage(style, save_to_file=True)
                    else:
                        print("❌ Please specify a style after 'cover'")
                    continue
                
                # Parse regular input
                style, params = calculator.parse_user_input(user_input)
                
                if style is None:
                    print(f"\n❌ Style not recognized!")
                    print(f"   Available styles: {', '.join(calculator.AVAILABLE_STYLES)}")
                    print(f"   Use 'cover <style>' to find minimal coverage")
                    continue
                
                print(f"\n🔎 Searching for style: {style}")
                if params:
                    print(f"   With parameters: {params}")
                
                calculator.print_combinations(style, params)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
    
    except Exception as e:
        print(f"❌ {e}")

if __name__ == "__main__":
    main()