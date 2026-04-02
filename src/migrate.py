import json
import sqlite3
import os
from database import init_db, add_defect
from engine import RoadAnalyzer

def migrate():
    init_db() # Создаем таблицу, если её нет
    analyzer = RoadAnalyzer()
    
    with open('data/defects.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for d in data:
        # Пересчитываем приоритет через наш Engine
        analysis = analyzer.calculate_priority(
            d['type'], d['size_cm'], d['traffic_level'], d.get('is_near_social', False)
        )
        # Добавляем в базу
        d.update(analysis)
        add_defect(d)
    
    print("✅ 50 точек успешно перенесены из JSON в SQLite!")

if __name__ == "__main__":
    migrate()