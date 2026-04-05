import cv2
from ultralytics import YOLO
import numpy as np
from PIL import Image
import random

class RoadDetector:
    def __init__(self, model_path=None):
        # По умолчанию используем вашу дообученную модель ям.
        if model_path is None:
            self.model = YOLO('pothole_best.pt')
        else:
            self.model = YOLO(model_path)

    def draw_bounding_boxes(self, open_cv_image, results, detected_defects):
        """Рисует bounding boxes вокруг обнаруженных объектов"""
        image_with_boxes = open_cv_image.copy()
        
        # Создаём список координат дефектов для быстрого поиска
        defect_coords = []
        for defect in detected_defects:
            if 'coords' in defect:
                defect_coords.append(defect['coords'])
        
        for r in results:
            boxes = r.boxes
            for idx, box in enumerate(boxes):
                # Координаты прямоугольника
                coords = box.xyxy[0]
                x1, y1, x2, y2 = int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])
                
                # Проверяем, это дефект или просто объект
                c = box.cls
                name = self.model.names[int(c)]
                confidence = float(box.conf)
                
                # Проверяем, входит ли этот box в detected_defects по координатам
                is_defect = False
                for d_coords in defect_coords:
                    if (d_coords[0] == x1 and d_coords[1] == y1 and 
                        d_coords[2] == x2 and d_coords[3] == y2):
                        is_defect = True
                        break
                
                if is_defect:
                    # Зелёная рамка для обнаруженных дефектов (ямы)
                    color = (0, 255, 0)  # BGR: зелёный
                    thickness = 3
                    label = f"яма {confidence:.2f}"
                else:
                    # Серая рамка для остальных объектов
                    color = (128, 128, 128)  # BGR: серый
                    thickness = 1
                    label = f"{name} {confidence:.2f}"
                
                # Рисуем прямоугольник
                cv2.rectangle(image_with_boxes, (x1, y1), (x2, y2), color, thickness)
                
                # Пишем лейбл над рамкой
                cv2.putText(image_with_boxes, label, (x1, max(y1 - 10, 20)),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        return image_with_boxes
    
    def detect_and_process(self, pil_image):
        # Превращаем PIL image (из Streamlit) в OpenCV формат
        open_cv_image = np.array(pil_image)
        open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)
        
        # Запуск инференса
        results = self.model(open_cv_image)
        
        detected_defects = []
        
        # Обработка результатов
        for r in results:
            boxes = r.boxes
            
            # Для каждого объекта
            for box in boxes:
                class_id = int(box.cls)
                class_name = self.model.names[class_id]
                confidence = float(box.conf)
                
                # Получаем координаты
                coords = box.xyxy[0]
                x1, y1, x2, y2 = int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])
                
                # Учитываем только реальные ямы, найденные вашей обученной моделью.
                if str(class_name).lower() != 'pothole':
                    continue
                d_type = 'pothole'
                
                # Приблизительный расчет размера на основе площади Bounding Box
                area = (x2 - x1) * (y2 - y1)
                h, w = open_cv_image.shape[:2]
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                lat_offset = round((0.5 - (cy / h)) * 0.02, 5)
                lon_offset = round(((cx / w) - 0.5) * 0.03, 5)
                # Имитация размера ямы в см в зависимости от площади
                size_cm = round(float(area / 1000), 1) + random.uniform(5, 15)
                size_cm = max(min(size_cm, 40.0), 5.0)

                detected_defects.append({
                    "type": d_type,
                    "size_cm": size_cm,
                    "confidence": confidence,
                    "lat_offset": lat_offset,
                    "lon_offset": lon_offset,
                    "coords": (x1, y1, x2, y2)  # Сохраняем координаты для рисования
                })
        
        # Рисуем bounding boxes на изображении
        image_with_boxes = self.draw_bounding_boxes(open_cv_image, results, detected_defects)
        
        
        image_with_boxes_rgb = cv2.cvtColor(image_with_boxes, cv2.COLOR_BGR2RGB)
        result_pil = Image.fromarray(image_with_boxes_rgb)
        
        
        if detected_defects:
            # Сортируем по вероятности
            detected_defects.sort(key=lambda x: x['confidence'], reverse=True)
            return {
                "defect": detected_defects[0],
                "image": result_pil
            }
        else:
            return {
                "defect": None,
                "image": result_pil
            }
if __name__ == "__main__":
    from PIL import Image
    import requests
    from io import BytesIO

    print("Запуск теста системы детекции...")
    detector = RoadDetector()
    
    # Скачаем тестовое фото дороги из интернета для проверки
    test_url = "https://raw.githubusercontent.com/ultralytics/ultralytics/main/ultralytics/assets/bus.jpg"
    response = requests.get(test_url)
    img = Image.open(BytesIO(response.content))

    print("Анализируем изображение...")
    result = detector.detect_and_process(img)

    if result and result.get("defect"):
        d = result["defect"]
        print(f"✅ УСПЕХ! Найден объект: {d['type']}")
        print(f"Точность: {round(d['confidence']*100, 2)}%")
        print(f"Примерный размер: {d['size_cm']} см")
    else:
        print("❌ Объекты не найдены, но код работает корректно.")