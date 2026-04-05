import sqlite3

def init_db():
    conn = sqlite3.connect('data/roadsense.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS defects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            lat REAL,
            lon REAL,
            size_cm REAL,
            traffic_level INTEGER,
            is_near_social BOOLEAN,
            score REAL,
            category TEXT,
            explanation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_defect(defect_data):
    conn = sqlite3.connect('data/roadsense.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO defects (type, lat, lon, size_cm, traffic_level, is_near_social, score, category, explanation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        defect_data['type'], defect_data['lat'], defect_data['lon'], 
        defect_data['size_cm'], defect_data['traffic_level'], 
        defect_data['is_near_social'], defect_data['score'], 
        defect_data['category'], defect_data['explanation']
    ))
    inserted_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return inserted_id


def delete_defect(defect_id):
    conn = sqlite3.connect('data/roadsense.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM defects WHERE id = ?', (defect_id,))
    deleted_rows = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_rows > 0


def save_defect(defect_data):
    """Совместимость с прототипом: сохраняет дефект и возвращает его ID."""
    return add_defect(defect_data)