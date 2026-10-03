import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import uvicorn
from app.ml_engine import MLEngine

app = FastAPI(title="Gesture Recognition API")

# Initialize MLEngine to load the model
ml = MLEngine(data_dir="../data", models_dir="../models")

class Landmark(BaseModel):
    x: float
    y: float
    z: float

class PredictRequest(BaseModel):
    landmarks: List[Landmark]

class PredictResponse(BaseModel):
    gesture: str
    confidence: float

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/model-info")
def model_info():
    if not ml.model:
        return {"status": "no_model"}
    return {
        "status": "loaded",
        "classes": ml.classes
    }

@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if not ml.model:
        raise HTTPException(status_code=503, detail="Model not trained/loaded")
    
    if len(req.landmarks) != 21:
        raise HTTPException(status_code=400, detail="Exactly 21 landmarks required")
        
    # MLEngine's normalize_landmarks can handle objects with x, y, z
    gesture, conf = ml.predict(req.landmarks)
    return PredictResponse(gesture=gesture, confidence=conf)

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
