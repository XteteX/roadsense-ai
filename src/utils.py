import json
import random
import os

def generate_almaty_defects(count=50):
    # Границы Алматы (примерные координаты)
    LAT_RANGE = (43.2000, 43.2700)
    LON_RANGE = (76.8500, 76.9500)
    
    defect_types = ["pothole", "crack", "faded_marking", "rutting"]
    traffic_levels = [1, 2, 3] # 1 - низкий, 3 - высокий
    
    defects = []
    
    for i in range(1, count + 1):
        defect = {
            "id": i,
            "type": random.choice(defect_types),
            "lat": round(random.uniform(*LAT_RANGE), 6),
            "lon": round(random.uniform(*LON_RANGE), 6),
            "size_cm": round(random.uniform(5.0, 40.0), 1),
            "traffic_level": random.choice(traffic_levels),
            "is_near_social": random.choice([True, False, False]), # 33% шанс близости к школе/больнице
            "detected_at": "2026-03-28T15:00:00Z"
        }
        defects.append(defect)
    
    # Создаем папку data, если её нет
    if not os.path.exists('data'):
        os.makedirs('data')
        
    with open('data/defects.json', 'w', encoding='utf-8') as f:
        json.dump(defects, f, ensure_ascii=False, indent=4)
    
    print(f"Успешно сгенерировано {count} точек в data/defects.json")

if __name__ == "__main__":
    generate_almaty_defects()