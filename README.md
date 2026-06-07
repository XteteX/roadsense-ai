
```markdown
# 🚧 RoadSense AI: Intelligent Road Monitoring in Almaty

**RoadSense AI** is a comprehensive computer vision-powered ecosystem for the automated detection, analysis, and prioritization of road defects.  

The project was developed specifically to digitalize the workflow of municipal services and the Akimat (city administration) of Almaty.

---

## 🎯 Project Mission

Shift from reactive pothole patching based on citizen complaints to **data-driven predictive urban management**.

---

## 🌟 Key Features

### 🤖 Citizen Monitoring (Telegram Bot)
- Data collection directly from city residents  
- Built-in AI filter screens out spam and irrelevant images (selfies, pets, etc.)

### 🧠 Explainable AI (XAI)
- The system automatically explains the severity and urgency of a defect  
- Factors considered:
  - Road type  
  - Traffic volume  
  - Proximity to critical social infrastructure (schools, hospitals)  

### 🗺️ Heatmaps
- Visualization of defect density across the city  
- Repair planning optimized at the district level rather than isolated points  

### ⚖️ Compliance with Standards
- ST RK 1218-2003  
- GOST 32883-2014  

### 📑 Turnkey Automation
- Automatic generation of PDF work orders  
- Photo confirmation attachments  
- Precise GPS coordinates  

---

## 🛠 Tech Stack

| Module | Technology |
|---|---|
| AI Core | YOLOv8 (Fine-tuned), OpenCV |
| Backend | FastAPI (Python), asynchronous architecture |
| Interface | Streamlit + Folium |
| Database | SQLite3 |
| Data Collection | Telegram Bot API (pyTelegramBotAPI) |
| Analytics | Scikit-learn |

---

## 📐 Prioritization Mathematical Model (XAI)

The defect priority score is calculated using the following formula:

$$P = (S \cdot w_1) + (T \cdot w_2) + (L \cdot w_3)$$

Where:
* **S** — defect area (detected by YOLOv8)
* **T** — traffic volume index
* **L** — social significance score
* **w₁, w₂, w₃** — weight coefficients

---

## 🚀 Quick Start Guide

### 1. System Preparation

Ensure you have Python 3.9+ installed.

```bash
# Clone the repository
git clone [https://github.com/XteteX/roadsense-ai.git](https://github.com/XteteX/roadsense-ai.git)
cd roadsense-ai

# Create a virtual environment
python -m venv .venv

# Activation

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

```

### 2. Running the Project

The system consists of two separate modules:

📊 **Management Dashboard**

```bash
streamlit run src/dashboard.py

```

🤖 **Telegram Bot**

```bash
python src/bot.py

```

---

## 📂 Project Structure

* `src/`         — core source code (bot, dashboard, processing logic)
* `data/`        — database storage and media files
* `models/`      — YOLOv8 model weights (`best.pt`)
* `assets/`      — UI images and architectural diagrams
* `requirements.txt` — project dependencies

---

## ⚠️ Limitations

* ❄️ **Weather:** reduced detection accuracy during heavy snow or dense fog
* 🌙 **Illumination:** suboptimal performance under low-light nighttime conditions
* 📍 **GPS:** standard positioning margin of error between 5–10 meters

---

## 🛣️ Roadmap

* [ ] Integration with "Sergek" city traffic cameras
* [ ] Automated analysis of road markings and traffic signs
* [ ] Predictive modeling for long-term road wear and tear

---

## 👥 Team

* **Oryntay Marlen** — Lead Developer / Backend / AI Architect
* **Dauletov Amirzhan** — AI Engineer / Frontend / UX Designer

---

## 📄 License

The project was developed as part of a hackathon. All rights reserved.

```

```
