import math

class RoadAnalyzer:
    """
    Класс для анализа дефектов дорожного покрытия, расчета приоритета ремонта
    и генерации текстовых обоснований (Explainability).
    """

    def __init__(self):
        # Веса типов дефектов: чем опаснее для авто, тем выше множитель
        self.type_weights = {
            "pothole": 1.5,        # Яма (самое опасное)
            "crack": 0.7,          # Трещина
            "faded_marking": 0.4,  # Стертая разметка
            "rutting": 1.1         # Колейность
        }
        
        # Перевод типов для объяснений
        self.type_labels = {
            "pothole": "выбоина",
            "crack": "трещина",
            "faded_marking": "износ разметки",
            "rutting": "колейность"
        }

    def calculate_priority(self, defect_type: str, size_cm: float, traffic_level: int, is_near_social: bool = False):
        """
        defect_type: тип дефекта (pothole, crack, etc.)
        size_cm: размер или глубина дефекта в см
        traffic_level: уровень трафика (1 - низкий, 2 - средний, 3 - высокий)
        is_near_social: находится ли рядом со школой, больницей и т.д.
        """
        
        # 1. Базовый балл на основе типа и размера
        weight = self.type_weights.get(defect_type, 1.0)
        base_score = weight * size_cm
        
        # 2. Модификатор трафика (высокий трафик ускоряет разрушение)
        traffic_multiplier = 1.0 + (traffic_level - 1) * 0.4
        
        # 3. Бонус за социальную значимость
        social_bonus = 15 if is_near_social else 0
        
        # Итоговый расчет
        final_score = (base_score * traffic_multiplier) + social_bonus
        
        # Ограничиваем шкалой от 0 до 100
        final_score = min(round(final_score, 1), 100)
        
        # Генерация категории срочности
        category = self._get_category(final_score)
        
        # Генерация объяснения
        explanation = self._generate_explanation(
            defect_type, size_cm, traffic_level, is_near_social, final_score
        )
        
        return {
            "score": final_score,
            "category": category,
            "explanation": explanation
        }

    def _get_category(self, score: float) -> str:
        if score >= 80: return "Критический"
        if score >= 50: return "Высокий"
        if score >= 25: return "Средний"
        return "Низкий (Плановый)"

    def _generate_explanation(self, d_type, size, traffic, social, score) -> str:
        label = self.type_labels.get(d_type, "дефект")
        reasons = []

        # Логика обоснования
        if size > 15:
            reasons.append(f"значительный размер {label} ({size} см)")
        else:
            reasons.append(f"наличие {label}")

        if traffic == 3:
            reasons.append("интенсивный транспортный поток (высокий риск ДТП)")
        elif traffic == 2:
            reasons.append("умеренная нагрузка на участок")

        if social:
            reasons.append("близость к социально значимым объектам")

        if score > 75 and d_type == "pothole":
            reasons.append("высокая вероятность повреждения подвески и потери управления")

        # Формируем итоговую фразу
        main_text = f"Приоритет {score}/100 обусловлен следующими факторами: " + ", ".join(reasons) + "."
        return main_text

# Пример для тестирования модуля
if __name__ == "__main__":
    analyzer = RoadAnalyzer()
    
    # Тест 1: Опасная яма на трассе
    result = analyzer.calculate_priority("pothole", 20, 3, is_near_social=True)
    print(f"Результат 1: {result['category']} - {result['score']}")
    print(f"Обоснование: {result['explanation']}\n")

    # Тест 2: Маленькая трещина во дворе
    result = analyzer.calculate_priority("crack", 5, 1)
    print(f"Результат 2: {result['category']} - {result['score']}")
    print(f"Обоснование: {result['explanation']}")