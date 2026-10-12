import os
import csv
import json
import math
import pickle
import numpy as np
from collections import Counter
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix

class MLEngine:
    def __init__(self, data_dir="data", models_dir="models"):
        self.data_dir = data_dir
        self.models_dir = models_dir
        
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
        
        self.dataset_path = os.path.join(self.data_dir, "gestures.csv")
        self.model_path = os.path.join(self.models_dir, "gesture_model.pkl")
        self.meta_path = os.path.join(self.models_dir, "gesture_metadata.json")
        self.cm_path = os.path.join(self.models_dir, "confusion_matrix.png")
        
        self.model = None
        self.classes = []
        
        self.dataset_stats = Counter()
        self._initialize_stats()
        
        self.last_saved_features = None
        self.smart_distance_threshold = 0.05
        
        self.load_model()
        
    def _initialize_stats(self):
        if not os.path.exists(self.dataset_path):
            return
        with open(self.dataset_path, mode='r') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if row: self.dataset_stats[row[0]] += 1

    def normalize_landmarks(self, landmarks):
        if not landmarks or len(landmarks) != 21:
            return None
            
        def get_coords(lm):
            if isinstance(lm, (tuple, list)):
                return lm[0], lm[1], (lm[2] if len(lm) > 2 else 0.0)
            return getattr(lm, 'x', 0.0), getattr(lm, 'y', 0.0), getattr(lm, 'z', 0.0)

        wrist = get_coords(landmarks[0])
        middle_mcp = get_coords(landmarks[9])
        
        scale = math.hypot(middle_mcp[0] - wrist[0], middle_mcp[1] - wrist[1])
        if scale < 0.001: scale = 0.001
        
        features = []
        for lm in landmarks:
            cx, cy, cz = get_coords(lm)
            nx = (cx - wrist[0]) / scale
            ny = (cy - wrist[1]) / scale
            nz = (cz - wrist[2]) / scale
            features.extend([nx, ny, nz])
            
        return features

    def augment_features(self, features):
        augmented = []
        features_np = np.array(features)
        
        augmented.append(features)
        
        noise = np.random.normal(0, 0.02, len(features))
        augmented.append((features_np + noise).tolist())
        
        scale_factor = np.random.uniform(0.9, 1.1)
        augmented.append((features_np * scale_factor).tolist())
        
        return augmented

    def save_sample(self, label, landmarks):
        # Standardize aliases
        if label in ["NXT_PAGE", "NEXT"]:
            label = "NEXT_PAGE"
        elif label in ["PREV_PAGE", "PREV"]:
            label = "PREVIOUS_PAGE"
        elif label in ["ZOOMIN"]:
            label = "ZOOM_IN"
        elif label in ["ZOOMOUT"]:
            label = "ZOOM_OUT"

        features = self.normalize_landmarks(landmarks)
        if not features: return False
        
        # Smart Sample Collection: prevent saving nearly identical frames
        if self.last_saved_features is not None:
            dist = np.linalg.norm(np.array(features) - np.array(self.last_saved_features))
            if dist < self.smart_distance_threshold:
                return False # Too similar, don't save
                
        self.last_saved_features = features
        
        file_exists = os.path.isfile(self.dataset_path)
        with open(self.dataset_path, mode='a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                header = ["label"] + [f"f_{i}" for i in range(len(features))]
                writer.writerow(header)
                
            row = [label] + features
            writer.writerow(row)
            
        self.dataset_stats[label] += 1
        return True

    def get_dataset_stats(self):
        return dict(self.dataset_stats)

    def clear_dataset(self):
        if os.path.exists(self.dataset_path):
            os.remove(self.dataset_path)
        self.dataset_stats.clear()
        self.last_saved_features = None

    def train_model(self):
        if not os.path.exists(self.dataset_path):
            return False, "Dataset not found."
            
        X, y = [], []
        with open(self.dataset_path, mode='r') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if not row: continue
                lbl = row[0]
                if lbl in ["NXT_PAGE", "NEXT"]: lbl = "NEXT_PAGE"
                elif lbl in ["PREV_PAGE", "PREV"]: lbl = "PREVIOUS_PAGE"
                elif lbl in ["ZOOMIN"]: lbl = "ZOOM_IN"
                elif lbl in ["ZOOMOUT"]: lbl = "ZOOM_OUT"
                y.append(lbl)
                X.append([float(val) for val in row[1:]])
                
        if len(X) < 10:
            return False, "Not enough samples to train."
            
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        aug_X_train, aug_y_train = [], []
        for feat, label in zip(X_train, y_train):
            augmented_feats = self.augment_features(feat)
            for a_feat in augmented_feats:
                aug_X_train.append(a_feat)
                aug_y_train.append(label)
                
        clf = RandomForestClassifier(n_estimators=100, max_depth=12, class_weight='balanced', random_state=42)
        clf.fit(aug_X_train, aug_y_train)
        
        y_pred = clf.predict(X_test)
        
        from sklearn.metrics import classification_report
        acc = accuracy_score(y_test, y_pred)
        cm = confusion_matrix(y_test, y_pred, labels=clf.classes_)
        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
        
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import seaborn as sns
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', xticklabels=clf.classes_, yticklabels=clf.classes_, cmap='Blues')
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        plt.title('Confusion Matrix')
        plt.tight_layout()
        plt.savefig(self.cm_path)
        plt.close()
        
        # Recommendations
        recommendations = []
        for cls in clf.classes_:
            if report[cls]['f1-score'] < 0.8:
                recommendations.append(f"Collect more varied samples for {cls} (F1: {report[cls]['f1-score']:.2f})")
                
        # Save Model
        with open(self.model_path, 'wb') as f:
            pickle.dump(clf, f)
            
        # Save Meta
        meta = {
            "classes": clf.classes_.tolist(),
            "samples": len(X),
            "accuracy": acc,
            "report": report,
            "cm": cm.tolist(),
            "recommendations": recommendations
        }
        with open(self.meta_path, 'w') as f:
            json.dump(meta, f, indent=4)
            
        self.model = clf
        self.classes = clf.classes_.tolist()
        
        return True, meta

    def load_model(self):
        if os.path.exists(self.model_path) and os.path.exists(self.meta_path):
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            with open(self.meta_path, 'r') as f:
                meta = json.load(f)
                self.classes = meta.get("classes", [])
            return True
        return False

    def predict(self, landmarks):
        if self.model is None:
            return "UNKNOWN", 0.0
            
        features = self.normalize_landmarks(landmarks)
        if not features: return "UNKNOWN", 0.0
        
        X = np.array(features).reshape(1, -1)
        probs = self.model.predict_proba(X)[0]
        max_idx = np.argmax(probs)
        confidence = probs[max_idx]
        label = self.classes[max_idx]
        
        return label, confidence
