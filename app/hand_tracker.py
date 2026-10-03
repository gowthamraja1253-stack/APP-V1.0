import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class HandTracker:
    def __init__(self, min_detection_confidence=0.7, min_tracking_confidence=0.7):
        base_options = python.BaseOptions(model_asset_path='assets/gesture_recognizer.task')
        options = vision.GestureRecognizerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_tracking_confidence
        )
        self.detector = vision.GestureRecognizer.create_from_options(options)

    def process_frame(self, frame, draw_landmarks=True):
        if frame is None:
            return frame, None, "Unknown", None
            
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        
        detection_result = self.detector.recognize(mp_image)
        
        handedness_str = "Unknown"
        landmarks_list = None
        canned_gesture = "None"
        
        if detection_result.hand_landmarks:
            hand_landmarks = detection_result.hand_landmarks[0]
            
            if detection_result.handedness:
                handedness_str = detection_result.handedness[0][0].category_name
                
            if detection_result.gestures and len(detection_result.gestures) > 0:
                canned_gesture = detection_result.gestures[0][0].category_name
            
            if draw_landmarks:
                # Custom drawing without drawing_utils for safety/simplicity in new API
                h, w, _ = frame.shape
                for lm in hand_landmarks:
                    x, y = int(lm.x * w), int(lm.y * h)
                    cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)
            
            landmarks_list = []
            for lm in hand_landmarks:
                landmarks_list.append((lm.x, lm.y))
                
        return frame, landmarks_list, handedness_str, canned_gesture
