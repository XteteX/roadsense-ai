import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
import os
import sys

# Добавляем путь к src, чтобы импортировать engine.py
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.engine import RoadAnalyzer

# Настройка страницы
st.set_page_config(page_title="RoadSense AI Dashboard", layout="wide", page_icon="🛣️")

# Инициализация анализатора
analyzer = RoadAnalyzer()

st.title("🛣️ RoadSense AI: Система мониторинга дорог Алматы")
st.markdown("---")

# Функция загрузки данных
@st.cache_data # Кешируем, чтобы не читать файл при каждом клике
def load_defects():
    filepath = os.path.join('data', 'defects.json')
    if not os.path.exists(filepath):
        st.error(f"Файл {filepath} не найден! Сначала запустите src/utils.py")
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        defects_raw = json.load(f)
    
    # Обрабатываем данные через Engine
    processed_defects = []
    for d in defects_raw:
        analysis = analyzer.calculate_priority(
            d['type'], d['size_cm'], d['traffic_level'], d['is_near_social']
        )
        # Объединяем исходные данные и анализ
        processed_defects.append({**d, **analysis})
        
    return processed_defects

# Загружаем 50 точек
defects = load_defects()

if defects:
    # Разделение экрана на колонки
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"Карта дефектов (Всего: {len(defects)} точек)")
        
        # Центр карты (Алматы)
        m = folium.Map(location=[43.2389, 76.8897], zoom_start=12)
        
        # Добавление меток
        for p in defects:
            # Выбор цвета в зависимости от категории ИИ
            color = "red" if p['category'] == "Критический" else \
                    "orange" if p['category'] == "Высокий" else \
                    "lightblue" if p['category'] == "Средний" else "green"
            
            folium.Marker(
                [p['lat'], p['lon']],
                popup=f"ID #{p['id']}: {p['score']}/100 ({p['category']})",
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(m)
        
        # Отрисовка карты
        st_folium(m, width="100%", height=600)

    with col2:
        st.subheader("📊 Аналитика ИИ и Обоснование")
        
        # Фильтр по критичности
        category_filter = st.selectbox(
            "Показать категорию:", 
            ["Все", "Критический", "Высокий", "Средний", "Низкий (Плановый)"]
        )
        
        # Сортировка по приоритету (сначала самые важные)
        df = pd.DataFrame(defects)
        df = df.sort_values(by="score", ascending=False)
        
        filtered_defects = df.to_dict('records')
        if category_filter != "Все":
            filtered_defects = [d for d in filtered_defects if d['category'] == category_filter]

        st.write(f"Отображено: {len(filtered_defects)} заявок")
        st.markdown("---")

        # Список заявок с объяснением
        for p in filtered_defects[:15]: # Показываем топ-15 для производительности
            icon = "🔴" if p['category'] == "Критический" else "🟠" if p['category'] == "Высокий" else "🟢"
            with st.expander(f"{icon} ID #{p['id']} - Приоритет {p['score']}"):
                st.write(f"**Тип:** {analyzer.type_labels.get(p['type'])}")
                st.write(f"**Размер:** {p['size_cm']} см")
                st.warning(f"**Вердикт ИИ:** {p['explanation']}")
                if st.button(f"Направить бригаду #{p['id']}"):
                    st.success("Наряд сформирован!")
else:
    st.warning("Нет данных для отображения. Убедитесь, что data/defects.json сгенерирован.")

# Сайдбар
st.sidebar.image("https://img.icons8.com/fluency/96/road.png", width=80)
st.sidebar.title("RoadSense AI")
st.sidebar.write("v1.0-MVP")
st.sidebar.markdown("---")
st.sidebar.write("**Статистика:**")
if defects:
    df_stat = pd.DataFrame(defects)
    st.sidebar.dataframe(df_stat['category'].value_counts())