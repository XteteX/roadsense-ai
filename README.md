# 🚧 RoadSense AI: Road Defect Monitoring Prototype for Almaty

RoadSense AI is a hackathon prototype that lets residents report potholes through a Telegram bot. A computer vision model checks each photo, and the system ranks confirmed reports by repair priority on a city dashboard.

Built in 10 days at **Decentrathon 5.0** (Top 5).

---

## 🌐 Live Demo

**[▶ Open RoadSense AI Dashboard](https://roadsense-ai-shfh8ssrifzngffcamzqpd.streamlit.app/)**

The map on the demo dashboard is pre-filled with **synthetic sample data** (`src/utils.py`), so you can see the heatmap and filters before real reports arrive.

---

## 🎯 Goal

Help city services move from handling complaints one at a time to planning repairs from aggregated, prioritised data.

---

## ✅ Project Status

| Component | Status | What it does now |
|---|---|---|
| Pothole detection | Working | Runs a pre-trained, open-source YOLOv8 pothole model (`pothole_best.pt`) on each photo |
| Telegram bot | Working | Accepts photos, rejects ones with no detected pothole, saves confirmed reports, skips duplicate messages |
| Priority scoring + explanation | Working | Scores each report from 0 to 100, assigns a category and writes a text explanation of the score |
| Dashboard | Working | Map with markers, defect-density heatmap, category filter, manual photo upload |
| Database | Working | SQLite stores reports and the bot's processed-message log |
| Defect size | Simulated | Estimated from the bounding-box area plus a random offset; not a real measurement |
| Location | Simulated | Derived from where the pothole appears in the image, offset from Almaty's centre; no real GPS yet |
| Traffic and nearby schools/hospitals | Manual / fixed | Set by sliders on the dashboard; the bot uses fixed defaults |
| REST API | Stub | FastAPI app with health-check endpoints only (`src/main.py`) |

---

## 🧠 How Priority Is Calculated

The rules in `src/engine.py` are written by hand. There is no trained model behind them, so every score can be explained.

```
score = type_weight × size_cm × (1 + 0.4 × (traffic_level − 1)) + social_bonus
```

| Term | Values |
|---|---|
| `type_weight` | pothole 1.5 · rutting 1.1 · crack 0.7 · faded marking 0.4 |
| `traffic_level` | 1 (low) · 2 (medium) · 3 (high) |
| `social_bonus` | +15 if a school or hospital is nearby, otherwise 0 |

The score is capped at 100 and mapped to a category:

| Score | Category |
|---|---|
| ≥ 80 | Critical |
| 50–79 | High |
| 25–49 | Medium |
| < 25 | Low (planned) |

Each report also gets a text explanation (generated in Russian). For a 30 cm pothole on a medium-traffic road near a school, the score is 1.5 × 30 × 1.4 + 15 = **78.0 (High)**, explained as:

> *Приоритет 78.0/100 обусловлен следующими факторами: значительный размер выбоина (30 см), умеренная нагрузка на участок, близость к социально значимым объектам, высокая вероятность повреждения подвески и потери управления.*
>
> (Priority 78.0/100 is driven by: large pothole size (30 cm), moderate traffic load, proximity to social infrastructure, high risk of suspension damage and loss of control.)

The detector only finds **potholes**. Cracks, rutting and faded markings appear in the synthetic sample data to show how the scoring and the map would work with more defect types.

---

## 🛠 Tech Stack

| Module | Technology |
|---|---|
| Detection | Ultralytics YOLOv8 (pre-trained pothole model), OpenCV |
| Bot | pyTelegramBotAPI |
| Dashboard | Streamlit, Folium, streamlit-folium |
| Database | SQLite3 |
| API (stub) | FastAPI |

---

## 🚀 Quick Start

Requires Python 3.11 (see `runtime.txt`).

```bash
git clone https://github.com/XteteX/roadsense-ai.git
cd roadsense-ai

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

**Optional: generate sample data**

```bash
python src/utils.py      # writes 50 synthetic defects to data/defects.json
```

**Run the dashboard**

```bash
streamlit run src/dashboard.py
```

**Run the Telegram bot**

```bash
# Linux / macOS
export TELEGRAM_BOT_TOKEN="your-token"
# Windows (PowerShell)
$env:TELEGRAM_BOT_TOKEN="your-token"

python -m src.bot        # run from the project root
```

---

## 📂 Project Structure

```
roadsense-ai/
├── src/
│   ├── bot.py          # Telegram bot: photo intake, validation, saving reports
│   ├── dashboard.py    # Streamlit dashboard: map, heatmap, filters, manual upload
│   ├── detection.py    # YOLOv8 inference and bounding-box drawing
│   ├── engine.py       # Priority scoring and text explanations
│   ├── database.py     # SQLite operations
│   ├── utils.py        # Synthetic sample-data generator
│   ├── migrate.py      # Imports data/defects.json into SQLite
│   └── main.py         # FastAPI stub (health checks)
├── data/
│   ├── defects.json    # Synthetic sample defects
│   └── roadsense.db    # SQLite database
├── pothole_best.pt     # Pre-trained open-source pothole detection weights
└── requirements.txt
```

---

## ⚠️ Known Limitations

- **The model was not trained by our team** and was not evaluated on Almaty roads, so its accuracy here is unknown.
- In testing it missed potholes in photos taken after rain, when the holes were filled with muddy water.
- Location and defect size are approximations (see Project Status), not measurements.
- The bot uses fixed traffic and "near school/hospital" values for every report.
- Any Telegram user can submit photos; there is no protection against manipulated or misleading images.

---

## 🛣️ Roadmap

- [ ] Read real GPS from Telegram location messages or photo EXIF data
- [ ] Collect and label local photos (rain, mud, snow, night) and fine-tune the detector on them
- [ ] Measure mAP on a held-out set of Almaty photos
- [ ] Look up traffic and nearby schools/hospitals from map data instead of fixed values
- [ ] Generate PDF work orders for repair crews
- [ ] Move the bot and dashboard onto a shared FastAPI backend

---

## 👥 Team

- **Marlen Oryntay**: team lead; AI integration, backend, Telegram bot, priority engine
- **Amirzhan Dauletov**: frontend, dashboard UX, presentation

---

## 🙏 Acknowledgements

Pothole detection weights (`pothole_best.pt`) come from an open-source pre-trained YOLOv8 model. *Add the original source link and its licence here.*

## 📄 License

Developed for the Decentrathon 5.0 hackathon. All rights reserved.
