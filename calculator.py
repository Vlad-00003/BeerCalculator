import json
import itertools
import re
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

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
    # Словарь для перевода стилей
    STYLE_TRANSLATION = {
        'Ale_1': 'Bristford Ale',
        'Hefeweizen_1': 'Hallbruck Hellas',
        'AmericanIpa_1': 'Cascadear IPA'
    }
    
    # Обратный словарь для поиска по пользовательскому вводу
    STYLE_REVERSE = {v.lower(): k for k, v in STYLE_TRANSLATION.items()}
    
    # Список доступных стилей
    AVAILABLE_STYLES = list(STYLE_TRANSLATION.values())
    
    # Значимые параметры
    VALID_PARAMS = ['Refreshment', 'Heaviness', 'Lightness', 'Acidity', 'Sweetness']
    
    def __init__(self, json_file_path: str):
        """
        Инициализация калькулятора с подготовленным JSON файлом
        """
        self.ingredients = self.load_ingredients_from_json(json_file_path)
        
        # Разделяем ингредиенты по типам
        self.malts = [i for i in self.ingredients if i.type == "Malts"]
        self.hops = [i for i in self.ingredients if i.type == "Hops"]
        self.yeast = [i for i in self.ingredients if i.type == "Yeast"]
        
        print(f"📊 Ingredients loaded: {len(self.ingredients)}")
        print(f"  🌾 Malts: {len(self.malts)}")
        print(f"  🌿 Hops: {len(self.hops)}")
        print(f"  🧪 Yeast: {len(self.yeast)}")
    
    def load_ingredients_from_json(self, file_path: str) -> List[Ingredient]:
        """
        Загружает ингредиенты из подготовленного JSON файла
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            ingredients = []
            for item in data:
                # Проверяем, что все необходимые поля есть
                if 'Name' not in item or 'Type' not in item or 'PerfectTemp' not in item:
                    print(f"⚠️ Ingredient skipped: required fields missing")
                    continue
                
                ingredient = Ingredient(
                    name=item['Name'],
                    type=item['Type'],
                    perfect_temp=item['PerfectTemp'],
                    style=item.get('Styles', {}),  # Если нет Styles, используем пустой словарь
                    params=item.get('Parameters', {})  # Если нет Parameters, используем пустой словарь
                )
                ingredients.append(ingredient)
            
            return ingredients
            
        except FileNotFoundError:
            raise Exception(f"❌ File {file_path} not found")
        except json.JSONDecodeError as e:
            raise Exception(f"❌ JSON format exception: {e}")
    
    def translate_style(self, style_code: str, to_user: bool = True) -> str:
        """
        Переводит стиль между кодом и пользовательским названием
        """
        if to_user:
            return self.STYLE_TRANSLATION.get(style_code, style_code)
        else:
            return self.STYLE_REVERSE.get(style_code.lower(), style_code)
    
    def parse_user_input(self, user_input: str) -> Tuple[Optional[str], Optional[List[str]]]:
        """
        Разбирает пользовательский ввод на стиль и параметры
        """
        user_input = user_input.strip()
        user_input_lower = user_input.lower()
        
        # Сортируем стили по длине для правильного поиска
        sorted_styles = sorted(self.STYLE_REVERSE.keys(), key=len, reverse=True)
        
        for style_lower in sorted_styles:
            if user_input_lower.startswith(style_lower):
                # Нашли стиль
                style_display = next(v for k, v in self.STYLE_TRANSLATION.items() 
                                   if v.lower() == style_lower)
                
                # Остаток строки - параметры
                remaining = user_input[len(style_lower):].strip()
                params = remaining.split() if remaining else None
                
                return style_display, params
        
        return None, None
    
    def calculate_result(self, malt: Ingredient, hop: Ingredient, yeast: Ingredient) -> Dict:
        """
        Рассчитывает результат комбинации трёх ингредиентов
        """
        # Определяем стиль
        style_scores = {}
        for ing in [malt, hop, yeast]:
            for style, weight in ing.style.items():
                style_scores[style] = style_scores.get(style, 0) + weight
        
        # Если нет стилей, возвращаем ошибку
        if not style_scores:
            return {
                'error': 'Нет данных о стилях',
                'malt': malt.name,
                'hop': hop.name,
                'yeast': yeast.name
            }
        
        # Находим максимальное значение
        sorted_styles = sorted(style_scores.items(), key=lambda x: x[1], reverse=True)
        max_score = sorted_styles[0][1]
        
        # Проверяем на ничью
        max_count = sum(1 for _, score in style_scores.items() if abs(score - max_score) < 0.01)
        is_tie = max_count >= 2
        
        if is_tie:
            result_style = sorted_styles[0][0]
            result_style_display = f"{self.translate_style(result_style)} ⚠️ (ничья)"
        else:
            result_style = sorted_styles[0][0]
            result_style_display = self.translate_style(result_style)
        
        # Определяем параметры
        param_scores = {}
        for ing in [malt, hop, yeast]:
            for param, value in ing.params.items():
                if param in self.VALID_PARAMS:  # Учитываем только значимые параметры
                    param_scores[param] = param_scores.get(param, 0) + value
        
        active_params = [param for param, value in param_scores.items() if value >= 10]
        
        # Формируем детали стилей для вывода
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
    
    def find_combinations(self, target_style_display: str, target_params: List[str] = None) -> List[Dict]:
        """
        Находит все комбинации для заданного стиля и параметров
        """
        target_style_code = self.translate_style(target_style_display, to_user=False)
        results = []
        
        total_combinations = len(self.malts) * len(self.hops) * len(self.yeast)
        print(f"  🔄 Checking {total_combinations} combinations...")
        
        for malt in self.malts:
            for hop in self.hops:
                for yeast in self.yeast:
                    result = self.calculate_result(malt, hop, yeast)
                    
                    # Пропускаем если ошибка
                    if 'error' in result:
                        continue
                    
                    # Проверяем стиль (учитываем, что при ничье style всё равно определён)
                    if result['style'] != target_style_code:
                        continue
                    
                    # Проверяем параметры
                    if target_params:
                        formatted_params = [p.capitalize() for p in target_params]
                        if not all(param in result['active_params'] for param in formatted_params):
                            continue
                    
                    results.append(result)
        
        return results
    
    def print_combinations(self, target_style: str, target_params: List[str] = None):
        """
        Выводит найденные комбинации
        """
        combinations = self.find_combinations(target_style, target_params)
        
        if not combinations:
            params_str = f" with attributes {target_params}" if target_params else ""
            print(f"\n❌ Combinations for {target_style}{params_str} not found")
            return
        
        print(f"\n✅ Found {len(combinations)} combinations for {target_style}")
        if target_params:
            print(f"📌 with attributes: {', '.join(target_params)}")
        print("=" * 80)
        
        for i, combo in enumerate(combinations, 1):
            print(f"\n🎯 --- Combination #{i} ---")
            print(f"  🌾 Malts: {combo['malt']}")
            print(f"  🌿 Hops: {combo['hop']}")
            print(f"  🧪 Yeast: {combo['yeast']}")
            print(f"  🍺 Result: {combo['style_display']}")
            
            if combo['is_tie']:
                print(f"     ⚠️ ATTENTION: Styles tied!")
            
            print(f"  📊 Style allocation: {', '.join(combo['style_details'])}")
            print(f"  ⚡ Active attributes: {', '.join(combo['active_params']) if combo['active_params'] else 'нет'}")
            print(f"  🌡️  Temperatures: Malt:{combo['perfect_temps']['malt']}°C, Hop:{combo['perfect_temps']['hop']}°C, Yeast:{combo['perfect_temps']['yeast']}°C")
            print(f"  📊 Attributes values:")
            
            # Сортируем параметры по убыванию
            sorted_params = sorted(combo['params'].items(), key=lambda x: x[1], reverse=True)
            for param, value in sorted_params:
                status = "✅" if value >= 10 else "❌"
                bar = "█" * int(value) + "░" * (10 - int(value))
                print(f"     {param:12}: {value:5.1f} {status} {bar}")
    
    def find_tie_combinations(self) -> List[Dict]:
        """
        Находит все комбинации с ничьёй
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
        Выводит все комбинации с ничьёй
        """
        combinations = self.find_tie_combinations()
        
        if not combinations:
            print("\n✅ Tie combinations not found")
            return
        
        print(f"\n⚠️ FOUND {len(combinations)} TIED COMBINATIONS")
        print("=" * 80)
        
        for i, combo in enumerate(combinations, 1):
            print(f"\n⚠️ --- Tie #{i} ---")
            print(f"  🌾 Malts: {combo['malt']}")
            print(f"  🌿 Hops: {combo['hop']}")
            print(f"  🧪 Yeast: {combo['yeast']}")
            print(f"  📊 Style allocation: {', '.join(combo['style_details'])}")
            print(f"  ⚡ Attributes values: {', '.join(combo['active_params']) if combo['active_params'] else 'нет'}")

def print_help():
    """Выводит справку по командам"""
    print("\n" + "="*60)
    print("📖 COMMANDS HELP")
    print("="*60)
    print("  🍺 STYLES:")
    print("     • Bristford Ale")
    print("     • Hallbruck Hellas")
    print("     • Cascadear IPA")
    print("\n  ⚡ ATTRIBUTES:")
    print("     • Refreshment, Heaviness, Lightness, Acidity, Sweetness")
    print("\n  📝 EXAMPLES:")
    print("     • Bristford Ale")
    print("     • Hallbruck Hellas lightness refreshment")
    print("     • cascadear ipa sweetness")
    print("\n  🛠️  COMMANDS:")
    print("     • ties - show all tied combinations")
    print("     • stats - shows statistics")
    print("     • help - show this info")
    print("     • exit - close calculator")
    print("="*60)

def main():
    """Основная функция"""
    print("="*60)
    print("🍺 BEET CRAFT CALCULATOR (simplified version)")
    print("="*60)
    
    # Укажи путь к подготовленному JSON файлу
    json_file = "ingredients.json"  # или используй другой файл
    
    try:
        calculator = CraftCalculator(json_file)
        print_help()
        
        while True:
            try:
                print("\n" + ">"*40)
                user_input = input("🔍 Enter your query: ").strip()
                
                if not user_input:
                    continue
                
                # Обработка команд
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
                
                # Разбираем ввод
                style, params = calculator.parse_user_input(user_input)
                
                if style is None:
                    print(f"\n❌ Unknown style!")
                    print(f"   Available styles: {', '.join(calculator.AVAILABLE_STYLES)}")
                    continue
                
                print(f"\n🔎 Searching for style: {style}")
                if params:
                    print(f"   with attributes: {params}")
                
                calculator.print_combinations(style, params)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Exception: {e}")
    
    except Exception as e:
        print(f"❌ {e}")

if __name__ == "__main__":
    main()