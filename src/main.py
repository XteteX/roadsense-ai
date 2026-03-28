from fastapi import FastAPI

app = FastAPI(title="RoadSense AI API")

@app.get("/")
def read_root():
    return {"status": "RoadSense AI is Online", "version": "1.0.0-MVP"}

@app.get("/health")
def health_check():
    return {"check": "completed", "result": "ready to analyze roads"}