import json
import os

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "pointer_size": 8,
    "pointer_style": "Dot",
    "pointer_trail": False,
    "trail_length": 10,
    "swipe_cooldown": 1.0,
    "pinch_cooldown": 0.5,
    "camera_id": 0,
    "show_landmarks": True,
    "show_gesture_guide": True,
    "page_timer": True,
    "recent_pdfs": [],
    
    # Advanced Gesture Thresholds
    "swipe_distance_threshold": 0.12,
    "swipe_direction_ratio": 1.1,
    "swipe_frame_window": 15,
    "pinch_start_threshold": 0.28,
    "pinch_release_threshold": 0.45,
    "landmark_smoothing_alpha": 0.5,
    "debug_mode": False,
    
    # ML Trained Recognition Settings
    "recognition_method": "HYBRID", # "MEDIA_PIPE_PRETRAINED", "TRAINED MODEL", "HYBRID", "GEOMETRIC RULES"
    "ml_confidence_threshold": 0.45,
    "ml_history_size": 4,
    "ml_cooldown": 0.6,
    "training_samples": 300
}

class SettingsManager:
    def __init__(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    self.settings.update(data)
            except Exception as e:
                print(f"Failed to load settings: {e}")

    def save(self):
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def get(self, key, default=None):
        val = self.settings.get(key, DEFAULT_SETTINGS.get(key))
        if val is None:
            return default
        return val

    def set(self, key, value):
        self.settings[key] = value
        self.save()
        
    def add_recent_pdf(self, path):
        recents = self.settings.get("recent_pdfs", [])
        if path in recents:
            recents.remove(path)
        recents.insert(0, path)
        self.settings["recent_pdfs"] = recents[:5] # Keep last 5
        self.save()
