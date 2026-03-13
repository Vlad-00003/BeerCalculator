import json
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Set

def clean_name(name: str) -> str:
    """
    Очищает название ингредиента от лишних слов
    """
    # Убираем "Большой мешок" в начале
    name = re.sub(r'^Большой мешок\s+', '', name)
    
    # Убираем "базового" если есть
    name = re.sub(r'^базового\s+', '', name)
    
    # Убираем тип ингредиента в разных падежах
    name = re.sub(r'^(солод|солода|хмель|хмеля|дрожжи|дрожжей)\s+', '', name, flags=re.IGNORECASE)
    
    # Убираем качество в конце
    name = re.sub(r'\s+(высокого|среднего|низкого)\s+качества$', '', name)
    
    return name.strip()

def extract_quality(name: str) -> str:
    """
    Извлекает качество из названия
    """
    quality_match = re.search(r'(высокого|среднего|низкого)\s+качества', name)
    return quality_match.group(1) if quality_match else 'стандартное'

def compare_values(val1, val2, tolerance: float = 0.01) -> bool:
    """
    Сравнивает два значения с учётом погрешности для float
    """
    if isinstance(val1, float) and isinstance(val2, float):
        return abs(val1 - val2) < tolerance
    return val1 == val2

def compare_dicts(dict1: Dict, dict2: Dict, dict_name: str) -> Tuple[bool, List[str]]:
    """
    Сравнивает два словаря и возвращает (совпадают, список различий)
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
    Упрощает JSON с ингредиентами:
    - Убирает лишние слова из названий
    - Убирает поле Rate из параметров
    - Объединяет все вариации одного компонента
    - Проверяет, что у всех вариаций одинаковые характеристики
    """
    
    # Читаем исходный JSON
    with open(input_file, 'r', encoding='utf-8') as f:
        ingredients = json.load(f)
    
    print(f"📦 Загружено ингредиентов: {len(ingredients)}")
    print("=" * 60)
    
    # Группируем по базовому названию и типу
    groups = defaultdict(list)
    for item in ingredients:
        base_name = clean_name(item['Name'])
        quality = extract_quality(item['Name'])
        
        # Убираем Rate из параметров
        clean_params = {k: v for k, v in item['Parameters'].items() if k != 'Rate'}
        
        group_key = (base_name, item['Type'])
        groups[group_key].append({
            'original_name': item['Name'],
            'quality': quality,
            'perfect_temp': item['PerfectTemp'],
            'styles': item['Styles'],
            'params': clean_params
        })
    
    print(f"\n🔍 Найдено уникальных компонентов: {len(groups)}")
    print("-" * 60)
    
    simplified = []
    has_inconsistencies = False
    
    # Обрабатываем каждую группу
    for (base_name, ing_type), variants in sorted(groups.items()):
        print(f"\n📦 Компонент: {base_name} ({ing_type})")
        print(f"   Вариантов: {len(variants)}")
        
        if len(variants) == 1:
            # Если только один вариант, просто добавляем его
            var = variants[0]
            simplified.append({
                'Name': base_name,
                'Type': ing_type,
                'PerfectTemp': var['perfect_temp'],
                'Styles': var['styles'],
                'Parameters': var['params']
            })
            print(f"   ✅ Единственный вариант")
            continue
        
        # Проверяем, что все варианты имеют одинаковые характеристики
        reference = variants[0]
        all_match = True
        inconsistencies = []
        
        for i, var in enumerate(variants[1:], 2):
            var_differences = []
            
            # Проверяем температуру
            if var['perfect_temp'] != reference['perfect_temp']:
                all_match = False
                var_differences.append(f"      Температура: {reference['perfect_temp']}°C vs {var['perfect_temp']}°C")
            
            # Проверяем стили
            styles_match, style_diffs = compare_dicts(reference['styles'], var['styles'], "Styles")
            if not styles_match:
                all_match = False
                var_differences.append("      Различия в стилях:")
                var_differences.extend(style_diffs)
            
            # Проверяем параметры
            params_match, param_diffs = compare_dicts(reference['params'], var['params'], "Parameters")
            if not params_match:
                all_match = False
                var_differences.append("      Различия в параметрах:")
                var_differences.extend(param_diffs)
            
            if var_differences:
                inconsistencies.append(f"\n   Вариант {i} ({var['quality']} качество):")
                inconsistencies.extend(var_differences)
        
        if all_match:
            # Все варианты одинаковые - берём любой (первый)
            simplified.append({
                'Name': base_name,
                'Type': ing_type,
                'PerfectTemp': reference['perfect_temp'],
                'Styles': reference['styles'],
                'Parameters': reference['params']
            })
            print(f"   ✅ Все {len(variants)} вариантов идентичны")
            print(f"      Качества: {', '.join(v['quality'] for v in variants)}")
        else:
            # Есть различия - выводим предупреждение
            has_inconsistencies = True
            print(f"   ⚠️  ВНИМАНИЕ! Обнаружены различия между вариантами:")
            
            # Показываем все варианты с их характеристиками
            for i, var in enumerate(variants, 1):
                print(f"\n      Вариант {i} ({var['quality']} качество):")
                print(f"         Оригинал: {var['original_name']}")
                print(f"         Температура: {var['perfect_temp']}°C")
                print(f"         Стили: {var['styles']}")
                print(f"         Параметры: {var['params']}")
            
            # Выводим детальные различия
            print(f"\n      Детальные различия:")
            for diff in inconsistencies:
                print(diff)
            
            # Всё равно добавляем все варианты отдельно
            print(f"\n      ➕ Добавляю все варианты отдельно")
            for var in variants:
                simplified.append({
                    'Name': f"{base_name} ({var['quality']})",
                    'Type': ing_type,
                    'PerfectTemp': var['perfect_temp'],
                    'Styles': var['styles'],
                    'Parameters': var['params']
                })
    
    # Сохраняем результат
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(simplified, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(f"\n✅ Упрощённый JSON сохранён в: {output_file}")
    print(f"📊 Итоговая статистика:")
    print(f"   Было ингредиентов: {len(ingredients)}")
    print(f"   Стало ингредиентов: {len(simplified)}")
    
    if has_inconsistencies:
        print("\n⚠️  ВНИМАНИЕ! Обнаружены компоненты с разными характеристиками:")
        print("   Они были сохранены как отдельные ингредиенты с указанием качества")
        print("   Проверьте данные в оригинальном файле")

def main():
    print("=" * 60)
    print("🛠️  УПРОЩЕНИЕ JSON С ИНГРЕДИЕНТАМИ")
    print("=" * 60)
    
    input_file = "ingredients.json"
    output_file = "ingredients_simplified.json"
    
    try:
        simplify_ingredients(input_file, output_file)
        
        print("\n" + "=" * 60)
        print("✅ ГОТОВО!")
        print("=" * 60)
        
    except FileNotFoundError:
        print(f"❌ Файл {input_file} не найден!")
    except json.JSONDecodeError:
        print(f"❌ Ошибка в формате JSON файла!")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()