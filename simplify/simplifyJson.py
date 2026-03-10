import json
import re
from collections import defaultdict

def simplify_ingredients(input_file: str, output_file: str = "ingredients_simplified.json"):
    """
    Упрощает JSON с ингредиентами:
    - Убирает "Большой мешок", "Солод", "Хмель", "Дрожжи" из названий
    - Убирает указания качества из названий
    - Убирает поле Rate из параметров
    - Оставляет только базовое название ингредиента
    """
    
    def clean_name(name: str) -> str:
        """
        Улучшенная очистка названия ингредиента от лишних слов
        """
        # Убираем "Большой мешок" в начале
        name = re.sub(r'^Большой мешок\s+', '', name)
        
        # Убираем "базового" если есть (может быть перед "солода")
        name = re.sub(r'^базового\s+', '', name)
        
        # Убираем тип ингредиента в разных падежах
        # Сначала пробуем убрать с окончаниями
        name = re.sub(r'^(солод|солода|хмель|хмеля|дрожжи|дрожжей)\s+', '', name, flags=re.IGNORECASE)
        
        # Убираем качество в конце (с предшествующим пробелом)
        name = re.sub(r'\s+(высокого|среднего|низкого)\s+качества$', '', name)
        
        # Финальная очистка от лишних пробелов
        return name.strip()
    
    def extract_quality(name: str) -> str:
        """
        Извлекает качество из названия для информации
        """
        quality_match = re.search(r'(высокого|среднего|низкого)\s+качества', name)
        return quality_match.group(1) if quality_match else 'стандартное'
    
    # Читаем исходный JSON
    with open(input_file, 'r', encoding='utf-8') as f:
        ingredients = json.load(f)
    
    print(f"📦 Загружено ингредиентов: {len(ingredients)}")
    
    # Группируем по базовому названию для анализа
    groups = defaultdict(list)
    simplified = []
    
    for item in ingredients:
        clean_item = item.copy()
        original_name = item['Name']
        
        # Очищаем название
        base_name = clean_name(original_name)
        clean_item['BaseName'] = base_name
        clean_item['Quality'] = extract_quality(original_name)
        clean_item['OriginalName'] = original_name  # сохраняем оригинал для справки
        
        # Убираем Rate из параметров
        if 'Parameters' in clean_item:
            clean_item['Parameters'] = {k: v for k, v in clean_item['Parameters'].items() 
                                      if k != 'Rate'}
        
        simplified.append(clean_item)
        
        # Группируем для статистики
        key = (base_name, clean_item['Type'])
        groups[key].append(clean_item)
    
    # Сохраняем упрощённый JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(simplified, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Упрощённый JSON сохранён в: {output_file}")
    
    # Выводим статистику
    print(f"\n📊 Статистика:")
    print(f"  Всего ингредиентов: {len(simplified)}")
    
    # Показываем группы дубликатов
    duplicate_groups = {k: v for k, v in groups.items() if len(v) > 1}
    if duplicate_groups:
        print(f"\n📦 Найдено групп с разным качеством:")
        for (base_name, ing_type), variants in sorted(duplicate_groups.items()):
            qualities = [v['Quality'] for v in variants]
            # Показываем оригинальные названия для отладки
            print(f"  • {base_name} ({ing_type}): {len(variants)} вариантов")
            for v in variants:
                print(f"    - {v['OriginalName']} → качество: {v['Quality']}")
    
    # Показываем уникальные ингредиенты
    unique_count = len(groups)
    print(f"\n🎯 Уникальных базовых ингредиентов: {unique_count}")
    
    return simplified

def create_merged_json(input_file: str, output_file: str = "ingredients_merged.json", 
                      strategy: str = 'separate'):
    """
    Создаёт ещё более упрощённый JSON, объединяя разные качества
    strategy: 'separate' - оставить все варианты отдельно
             'average' - усреднить все варианты
             'best' - оставить только лучшее качество
    """
    
    def clean_name(name: str) -> str:
        """
        Улучшенная очистка названия для группировки
        """
        # Убираем "Большой мешок"
        name = re.sub(r'^Большой мешок\s+', '', name)
        
        # Убираем "базового"
        name = re.sub(r'^базового\s+', '', name)
        
        # Убираем тип ингредиента
        name = re.sub(r'^(солод|солода|хмель|хмеля|дрожжи|дрожжей)\s+', '', name, flags=re.IGNORECASE)
        
        # Убираем качество
        name = re.sub(r'\s+(высокого|среднего|низкого)\s+качества$', '', name)
        
        return name.strip()
    
    def extract_quality_score(name: str) -> int:
        """Преобразует качество в числовой рейтинг"""
        if 'высокого' in name:
            return 3
        elif 'среднего' in name:
            return 2
        elif 'низкого' in name:
            return 1
        else:
            return 2  # стандартное = среднее
    
    # Читаем исходный JSON
    with open(input_file, 'r', encoding='utf-8') as f:
        ingredients = json.load(f)
    
    print(f"\n📦 Обработка {len(ingredients)} ингредиентов...")
    
    # Группируем по базовому названию
    groups = defaultdict(list)
    for item in ingredients:
        base_name = clean_name(item['Name'])
        # Добавляем отладочный вывод для проблемных случаев
        if 'Coldra' in item['Name']:
            print(f"  Оригинал: '{item['Name']}' → Базовое: '{base_name}'")
        
        item_with_base = item.copy()
        item_with_base['BaseName'] = base_name
        item_with_base['QualityScore'] = extract_quality_score(item['Name'])
        groups[(base_name, item['Type'])].append(item_with_base)
    
    print(f"\n📊 Найдено уникальных групп: {len(groups)}")
    
    merged = []
    
    for (base_name, ing_type), variants in groups.items():
        if strategy == 'separate' or len(variants) == 1:
            # Оставляем все варианты отдельно
            for var in variants:
                clean_var = {
                    'Name': base_name,
                    'Type': ing_type,
                    'PerfectTemp': var['PerfectTemp'],
                    'Styles': var['Styles'],
                    'Parameters': {k: v for k, v in var['Parameters'].items() if k != 'Rate'}
                }
                merged.append(clean_var)
        
        elif strategy == 'best':
            # Берём вариант с наивысшим качеством
            best = max(variants, key=lambda x: x['QualityScore'])
            print(f"  Группа '{base_name}': выбрано лучшее качество из {len(variants)} вариантов")
            
            clean_var = {
                'Name': base_name,
                'Type': ing_type,
                'PerfectTemp': best['PerfectTemp'],
                'Styles': best['Styles'],
                'Parameters': {k: v for k, v in best['Parameters'].items() if k != 'Rate'}
            }
            merged.append(clean_var)
        
        elif strategy == 'average':
            # Усредняем все параметры
            print(f"  Группа '{base_name}': усреднение {len(variants)} вариантов")
            
            avg_params = {}
            avg_styles = {}
            total_temp = 0
            
            # Собираем все параметры
            all_params = set()
            all_styles = set()
            for var in variants:
                all_params.update(var['Parameters'].keys())
                all_styles.update(var['Styles'].keys())
            
            # Усредняем
            for param in all_params:
                if param == 'Rate':
                    continue
                values = [var['Parameters'].get(param, 0) for var in variants]
                avg_params[param] = sum(values) / len(variants)
            
            for style in all_styles:
                values = [var['Styles'].get(style, 0) for var in variants]
                avg_styles[style] = sum(values) / len(variants)
            
            avg_temp = sum(var['PerfectTemp'] for var in variants) // len(variants)
            
            clean_var = {
                'Name': base_name,
                'Type': ing_type,
                'PerfectTemp': avg_temp,
                'Styles': avg_styles,
                'Parameters': avg_params
            }
            merged.append(clean_var)
    
    # Сохраняем результат
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Объединённый JSON сохранён в: {output_file}")
    print(f"  Стратегия: {strategy}")
    print(f"  Было: {len(ingredients)} -> Стало: {len(merged)} ингредиентов")
    
    return merged

def inspect_problematic_names(input_file: str):
    """
    Функция для отладки - показывает все уникальные базовые названия
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        ingredients = json.load(f)
    
    def clean_name(name: str) -> str:
        name = re.sub(r'^Большой мешок\s+', '', name)
        name = re.sub(r'^базового\s+', '', name)
        name = re.sub(r'^(солод|солода|хмель|хмеля|дрожжи|дрожжей)\s+', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+(высокого|среднего|низкого)\s+качества$', '', name)
        return name.strip()
    
    print("\n🔍 АНАЛИЗ НАЗВАНИЙ:")
    print("-" * 50)
    
    groups = defaultdict(list)
    for item in ingredients:
        base = clean_name(item['Name'])
        groups[base].append(item['Name'])
    
    for base, originals in sorted(groups.items()):
        if len(originals) > 1:
            print(f"\n📦 '{base}' -> {len(originals)} вариантов:")
            for orig in originals:
                print(f"    • {orig}")

def main():
    print("="*60)
    print("🛠️  УПРОЩЕНИЕ JSON С ИНГРЕДИЕНТАМИ")
    print("="*60)
    
    input_file = "ingredients.json"
    
    # Сначала анализируем проблемные названия
    inspect_problematic_names(input_file)
    
    print("\n" + "="*60)
    
    # Вариант 1: Простое упрощение (сохраняем все варианты, но чистим названия)
    # print("\n1️⃣ ПРОСТОЕ УПРОЩЕНИЕ")
    # print("-" * 40)
    # simplify_ingredients(input_file, "ingredients_simplified.json")
    
    # Вариант 2: Объединение с разными стратегиями
    print("\n2️⃣ ОБЪЕДИНЕНИЕ ВАРИАНТОВ")
    print("-" * 40)
    
    # print("\n📌 Стратегия: separate (все варианты отдельно)")
    # create_merged_json(input_file, "ingredients_merged_separate.json", strategy='separate')
    
    print("\n📌 Стратегия: best (только лучшее качество)")
    create_merged_json(input_file, "ingredients_merged_best.json", strategy='best')
    
    # print("\n📌 Стратегия: average (усреднение)")
    # create_merged_json(input_file, "ingredients_merged_average.json", strategy='average')
    
    print("\n" + "="*60)
    print("✅ ГОТОВО! Файлы сохранены:")
    print("  • ingredients_simplified.json - очищенные названия, все варианты")
    print("  • ingredients_merged_separate.json - базовые названия, все варианты")
    print("  • ingredients_merged_best.json - только лучшее качество")
    print("  • ingredients_merged_average.json - усреднённые значения")
    print("="*60)

if __name__ == "__main__":
    main()