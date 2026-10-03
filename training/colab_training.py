"""
Google Colab Training Script for Touchless PDF Controller

Instructions for Google Colab:
1. Open Google Colab (colab.research.google.com)
2. Upload `gestures.csv` from your `data/` folder to Colab.
3. Paste this entire script into a cell and run it.
4. Download the generated `gesture_model.pkl` and `gesture_metadata.json`
5. Place them in your desktop `models/` folder.
"""

import pandas as pd
import numpy as np
import json
import pickle
import math
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import matplotlib.pyplot as plt
import seaborn as sns

def augment_features(features):
    augmented = []
    features_np = np.array(features)
    augmented.append(features) # original
    
    # Noise
    noise = np.random.normal(0, 0.02, len(features))
    augmented.append((features_np + noise).tolist())
    
    # Scale
    scale_factor = np.random.uniform(0.9, 1.1)
    augmented.append((features_np * scale_factor).tolist())
    return augmented

print("Loading dataset...")
df = pd.read_csv('gestures.csv')
X_raw = df.iloc[:, 1:].values.tolist()
y_raw = df.iloc[:, 0].values.tolist()

X_train, X_test, y_train, y_test = train_test_split(X_raw, y_raw, test_size=0.2, random_state=42, stratify=y_raw)

print("Augmenting training data...")
aug_X_train, aug_y_train = [], []
for feat, label in zip(X_train, y_train):
    for a_feat in augment_features(feat):
        aug_X_train.append(a_feat)
        aug_y_train.append(label)

print(f"Training on {len(aug_X_train)} samples...")
clf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
clf.fit(aug_X_train, aug_y_train)

y_pred = clf.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"Test Accuracy: {acc*100:.2f}%")

cm = confusion_matrix(y_test, y_pred, labels=clf.classes_)
plt.figure(figsize=(8,6))
sns.heatmap(cm, annot=True, fmt='d', xticklabels=clf.classes_, yticklabels=clf.classes_, cmap='Blues')
plt.title("Confusion Matrix")
plt.show()

report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
for cls in clf.classes_:
    if report[cls]['f1-score'] < 0.8:
        print(f"WARNING: Low accuracy for {cls}. Consider collecting more varied samples.")

with open('gesture_model.pkl', 'wb') as f:
    pickle.dump(clf, f)

meta = {
    "classes": clf.classes_.tolist(),
    "samples": len(X_raw),
    "accuracy": acc,
    "cm": cm.tolist()
}
with open('gesture_metadata.json', 'w') as f:
    json.dump(meta, f, indent=4)

print("Training complete! Download gesture_model.pkl and gesture_metadata.json")
