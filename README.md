# Touchless PDF & Presentation Controller

A touchless gesture-controlled PDF presentation system built with Python, OpenCV, and MediaPipe. 
Control your presentation using a regular webcam—without any specialized hardware.

## Features

- **Hybrid Gesture Recognition:** Combines MediaPipe pretrained models, custom ML classification, and dynamic swipe calculations for highest reliability.
- **Dynamic Swipe Detection:** Robust time-series analysis prevents accidental page changes and requires a confident "Swipe Left/Right" hand movement over a series of frames.
- **Presentation Mode:** Distraction-free maximized PDF viewing.
- **PDF Pointer:** Point at the screen to display a red cursor.
- **Pinch-to-Zoom:** Natural two-finger zooming in/out of PDF pages.
- **Gesture Training Studio:** Built-in UI to securely capture custom gesture samples and train personalized models.

---

## 🚀 How to Setup and Run

### 1. Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
*(Dependencies include OpenCV, MediaPipe, PyMuPDF, CustomTkinter, NumPy, FastAPI, Seaborn, Matplotlib, and Scikit-Learn).*

### 2. Run the App
```bash
python main.py
```

---

## 🛠 Model Management & Training Guide

The default setup uses a highly reliable **HYBRID** engine. However, you can train a custom gesture model using your own hand poses.

### A. How to Collect Your Dataset
1. Open the application.
2. Click **Train Gestures** in the sidebar.
3. Select a gesture (e.g. `NEXT_PAGE`) from the dropdown.
4. Click **START RECORDING** and move your hand around (change distance, angle, lighting). 
5. *Smart Collection* automatically ignores identical frames, ensuring a highly varied dataset.
6. Collect at least **150+ samples** per class. Don't forget to collect a large `NEUTRAL` class!

### B. How to Train in Google Colab (Recommended)
Training on a desktop is fast, but Colab ensures a stable environment.
1. Open Google Colab (colab.research.google.com).
2. Upload the `data/gestures.csv` file from your desktop to Colab.
3. Open `training/colab_training.py` in your desktop editor, copy its contents, and paste it into a Colab cell.
4. Run the cell.

### C & D. How to Export & Install the Model
1. Once the Colab script finishes, it will generate `gesture_model.pkl` and `gesture_metadata.json`.
2. Download these files.
3. Place them into the `models/` directory of this project.
4. The local application will automatically load them on startup!

### E. How to Run the Optional FastAPI Server
If you prefer running inference in a separate process:
```bash
# In a new terminal
source venv/bin/activate
cd touchless-pdf-controller
python api/server.py
```
*Note: The desktop app natively runs the model offline so the API is optional and strictly for integrating with external tooling.*

### F. How to Switch Recognition Modes
1. Click the **Settings (⚙)** button in the application.
2. Under **Recognition Method**, select your preferred engine:
   - **HYBRID (Default & Recommended):** Blends dynamic swipe math, pretrained gestures, and ML models.
   - **MEDIA_PIPE_PRETRAINED:** Uses strictly Google's pretrained gestures.
   - **TRAINED MODEL:** Strictly relies on your custom `gesture_model.pkl`.
   - **GEOMETRIC RULES:** Math-based tracking.

### G. How to Add a New Gesture
1. Open the **Training Studio**.
2. Type a new name in the **"New Custom Gesture"** box and click **Add Class**.
3. Record samples.
4. To make the gesture actually do something, open `app/gesture_engine.py` and add logic for your custom class name inside the `_detect_hybrid` fallback!
