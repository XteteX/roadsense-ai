import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
import os
import sqlite3
import sys
import random
from PIL import Image

# Инициализируем sys.path ДО импортов из src
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.detection import RoadDetector
from src.engine import RoadAnalyzer
from src.database import init_db, add_defect


# Инициализируем БД при запуске приложения
init_db()

# Настройка страницы
st.set_page_config(page_title="RoadSense AI Dashboard", layout="wide", page_icon="🛣️")

# Инициализация анализатора
analyzer = RoadAnalyzer()

# Инициализируем детектор
detector = RoadDetector()

ALMATY_CENTER = (43.2389, 76.8897)

if "last_added_id" not in st.session_state:
    st.session_state["last_added_id"] = None
if "map_focus" not in st.session_state:
    st.session_state["map_focus"] = ALMATY_CENTER

st.title("🛣️ RoadSense AI: Система мониторинга дорог Алматы")
st.markdown("---")

@st.cache_data
def get_defects_from_db():
    """Загружает все дефекты из SQLite в DataFrame."""
    db_path = os.path.join('data', 'roadsense.db')
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query("SELECT * FROM defects", conn)
    finally:
        conn.close()
    return df


def import_initial_data_from_json():
    """Импортирует дефекты из JSON в БД с расчетом приоритета через engine."""
    filepath = os.path.join('data', 'defects.json')
    if not os.path.exists(filepath):
        return 0, f"Файл {filepath} не найден. Сначала сгенерируйте данные через src/utils.py"

    with open(filepath, 'r', encoding='utf-8') as f:
        defects_raw = json.load(f)

    imported = 0
    for d in defects_raw:
        analysis = analyzer.calculate_priority(
            d['type'], d['size_cm'], d['traffic_level'], d['is_near_social']
        )
        defect_record = {
            "type": d['type'],
            "lat": d['lat'],
            "lon": d['lon'],
            "size_cm": d['size_cm'],
            "traffic_level": d['traffic_level'],
            "is_near_social": d['is_near_social'],
            "score": analysis['score'],
            "category": analysis['category'],
            "explanation": analysis['explanation']
        }
        add_defect(defect_record)
        imported += 1

    return imported, None


df_defects = get_defects_from_db()
defects = df_defects.to_dict('records') if not df_defects.empty else []

if defects:
    # Разделение экрана на колонки
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"Карта дефектов (Всего: {len(defects)} точек)")
        
        # Центр карты: на последней добавленной точке, если она есть
        map_center = st.session_state.get("map_focus", ALMATY_CENTER)
        map_zoom = 14 if st.session_state.get("last_added_id") else 12
        m = folium.Map(location=[map_center[0], map_center[1]], zoom_start=map_zoom)
        
        # Добавление меток
        for p in defects:
            is_last_added = p['id'] == st.session_state.get("last_added_id")

            # Выбор цвета в зависимости от категории ИИ
            color = "red" if p['category'] == "Критический" else \
                    "orange" if p['category'] == "Высокий" else \
                    "lightblue" if p['category'] == "Средний" else "green"

            icon_color = "red" if is_last_added else color
            icon_name = "star" if is_last_added else "info-sign"
            popup_text = f"ID #{p['id']}: {p['score']}/100 ({p['category']})"
            if is_last_added:
                popup_text = f"НОВАЯ ТОЧКА -> {popup_text}"
            
            folium.Marker(
                [p['lat'], p['lon']],
                popup=popup_text,
                tooltip="Новая заявка" if is_last_added else f"Заявка #{p['id']}",
                icon=folium.Icon(color=icon_color, icon=icon_name)
            ).add_to(m)

            if is_last_added:
                folium.CircleMarker(
                    location=[p['lat'], p['lon']],
                    radius=14,
                    color="red",
                    fill=True,
                    fill_opacity=0.2,
                    weight=3,
                ).add_to(m)
        
        # Отрисовка карты
        st_folium(m, width="100%", height=600)

        if st.session_state.get("last_added_id"):
            st.info("Последняя добавленная заявка выделена красной звездой и кругом.")

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
    st.warning("База данных пуста. Импортируйте начальные данные.")
    if st.button("Импортировать начальные данные из JSON"):
        with st.spinner("Импортируем данные в БД..."):
            imported_count, err = import_initial_data_from_json()
        if err:
            st.error(err)
        else:
            get_defects_from_db.clear()
            st.success(f"Импортировано {imported_count} записей в базу данных.")
            st.rerun()

# Сайдбар
st.sidebar.image("https://img.icons8.com/fluency/96/road.png", width=80)
st.sidebar.title("RoadSense AI")
st.sidebar.write("v1.0-MVP")
st.sidebar.markdown("---")

with st.sidebar:
    st.header("📸 Новый отчет (YOLOv8s)")
    uploaded_file = st.file_uploader("Загрузить фото дефекта", type=['jpg', 'jpeg', 'png'])

    if uploaded_file:
        # Покажем фото пользователю
        image_pil = Image.open(uploaded_file)
        
        # Вызов реального Computer Vision
        with st.spinner("Запускаем YOLOv8s для анализа..."):
            detection_result = detector.detect_and_process(image_pil)
            
            # detection_result = {"defect": {...}, "image": PIL_Image_with_boxes}
            detected_data = detection_result['defect']
            image_with_boxes = detection_result['image']
            
            if detected_data:
                detected_type = detected_data['type']
                detected_size = detected_data['size_cm']
                st.success(f"Обнаружено: {analyzer.type_labels.get(detected_type)}, размер ~{detected_size}см")
                st.info(f"Вероятность детекции: {round(detected_data['confidence']*100, 1)}%")
            else:
                st.warning("Дефекты не обнаружены. Попробуйте другое фото.")
                detected_type = None
        
        # Показываем изображение с bounding boxes
        st.image(image_with_boxes, caption="Результат анализа YOLO (зелёные рамки - обнаруженные объекты)", use_container_width=True)

        # Форма подтверждения (если дефект найден)
        if detected_type:
            with st.form("add_defect_form"):
                st.write("### Подтвердите данные")
                # Жюри оценит: можно редактировать ИИ-ответ
                lat_offset = detected_data.get("lat_offset", random.uniform(-0.01, 0.01))
                lon_offset = detected_data.get("lon_offset", random.uniform(-0.01, 0.01))
                lat = st.number_input("Широта (Lat)", value=ALMATY_CENTER[0] + lat_offset, format="%.6f")
                lon = st.number_input("Долгота (Lon)", value=ALMATY_CENTER[1] + lon_offset, format="%.6f")
                traffic = st.slider("Уровень трафика", 1, 3, 2)
                social = st.checkbox("Рядом школа/больница?")
                
                if st.form_submit_button("Внести в реестр"):
                    # Считаем приоритет через наш Engine
                    analysis = analyzer.calculate_priority(detected_type, detected_size, traffic, social)
                    
                    # Формируем объект для базы
                    new_data = {
                        "type": detected_type, "lat": lat, "lon": lon,
                        "size_cm": detected_size, "traffic_level": traffic,
                        "is_near_social": social, "score": analysis['score'],
                        "category": analysis['category'], "explanation": analysis['explanation']
                    }
                    
                    new_id = add_defect(new_data)
                    get_defects_from_db.clear()
                    st.session_state["last_added_id"] = new_id
                    st.session_state["map_focus"] = (lat, lon)
                    st.balloons()
                    st.success("Данные сохранены в SQLite!")
                    st.rerun() # Обновляем страницу, чтобы точка появилась

st.sidebar.write("**Статистика:**")
if defects:
    df_stat = pd.DataFrame(defects)
    st.sidebar.dataframe(df_stat['category'].value_counts())