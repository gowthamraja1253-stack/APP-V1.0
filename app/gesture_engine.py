import time
import math
from collections import deque
from .ml_engine import MLEngine

class GestureEngine:
    def __init__(self, settings_manager):
        self.settings = settings_manager
        
        # Temporal Tracking for Swipes
        self.swipe_history = deque(maxlen=self.settings.get("swipe_frame_window"))
        
        # ML Tracking
        self.ml_engine = MLEngine()
        self.prediction_history = deque(maxlen=10)
        
        # Cooldowns
        self.last_action_time = 0
        
        # Pinch State
        self.pinch_state = "OPEN"
        self.initial_pinch_dist = None
        
        # Pointer smoothing
        self.smooth_ptr_x = None
        self.smooth_ptr_y = None
        
        self.debug_data = {}

    def reset_state(self):
        self.swipe_history.clear()
        self.prediction_history.clear()
        self.pinch_state = "OPEN"
        self.initial_pinch_dist = None
        self.smooth_ptr_x = None
        self.smooth_ptr_y = None

    def _is_pointer_active_geometric(self, landmarks):
        if not landmarks: return False
        index_up = landmarks[8][1] < landmarks[6][1]
        middle_down = landmarks[12][1] > landmarks[10][1]
        ring_down = landmarks[16][1] > landmarks[14][1]
        pinky_down = landmarks[20][1] > landmarks[18][1]
        return index_up and middle_down and ring_down and pinky_down

    def detect_gesture(self, landmarks, handedness="Unknown", frame_width=640, frame_height=480, canned_gesture="None"):
        current_time = time.time()
        
        if not landmarks:
            self.reset_state()
            self.debug_data = {"status": "NO HAND"}
            return "None", None, "WAITING", self.debug_data

        # Smoothing for pointer (always computed)
        alpha = self.settings.get("landmark_smoothing_alpha", 0.5)
        raw_x, raw_y = landmarks[8][0], landmarks[8][1]
        if self.smooth_ptr_x is None:
            self.smooth_ptr_x, self.smooth_ptr_y = raw_x, raw_y
        else:
            self.smooth_ptr_x = (alpha * raw_x) + ((1 - alpha) * self.smooth_ptr_x)
            self.smooth_ptr_y = (alpha * raw_y) + ((1 - alpha) * self.smooth_ptr_y)
            
        self.swipe_history.append((self.smooth_ptr_x, self.smooth_ptr_y, current_time))
        
        method = self.settings.get("recognition_method", "HYBRID")
        
        # Priority 1: Cooldown filtering
        if (current_time - self.last_action_time) < self.settings.get("ml_cooldown", 0.8):
            return "Pointer", (self.smooth_ptr_x, self.smooth_ptr_y), "TRACKING", self.debug_data

        if method == "MEDIA_PIPE_PRETRAINED":
            return self._detect_pretrained(landmarks, canned_gesture, current_time)
        elif method == "TRAINED MODEL":
            return self._detect_ml_only(landmarks, current_time)
        else:
            return self._detect_hybrid(landmarks, canned_gesture, current_time, handedness)

    def _check_dynamic_swipe(self, current_time):
        if len(self.swipe_history) < self.swipe_history.maxlen:
            return None
            
        start_x, start_y, start_time = self.swipe_history[0]
        end_x, end_y, end_time = self.swipe_history[-1]
        
        dx = end_x - start_x
        dy = end_y - start_y
        duration = end_time - start_time
        if duration <= 0: return None
        
        velocity = abs(dx) / duration
        
        self.debug_data["swipe_dx"] = round(dx, 3)
        self.debug_data["swipe_dy"] = round(dy, 3)
        self.debug_data["swipe_vel"] = round(velocity, 3)
        
        dist_thresh = self.settings.get("swipe_distance_threshold", 0.15)
        dir_ratio = self.settings.get("swipe_direction_ratio", 1.5)
        
        if abs(dx) > dist_thresh and abs(dx) > abs(dy) * dir_ratio:
            self.last_action_time = current_time
            self.swipe_history.clear()
            self.prediction_history.clear()
            if dx < 0:
                return "Swipe Left"
            else:
                return "Swipe Right"
        return None

    def _detect_hybrid(self, landmarks, canned_gesture, current_time, handedness):
        self.debug_data["method"] = "HYBRID"
        
        # 1. Dynamic Swipe Priority
        swipe = self._check_dynamic_swipe(current_time)
        if swipe:
            return swipe, None, "CONFIRMED", self.debug_data

        # 2. Canned Gesture Override (Extremely High Confidence)
        if canned_gesture == "Pointing_Up":
            self.prediction_history.clear()
            return "Pointer", (self.smooth_ptr_x, self.smooth_ptr_y), "TRACKING", self.debug_data
            
        if canned_gesture == "Closed_Fist":
            self.prediction_history.clear()
            return "None", None, "TRACKING", self.debug_data
            
        # 3. Geometric Pinch fallback
        wrist = landmarks[0]
        middle_mcp = landmarks[9]
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        hand_scale = math.hypot(middle_mcp[0] - wrist[0], middle_mcp[1] - wrist[1])
        if hand_scale < 0.01: hand_scale = 0.01
        
        raw_pinch_dist = math.hypot(index_tip[0] - thumb_tip[0], index_tip[1] - thumb_tip[1])
        normalized_pinch = raw_pinch_dist / hand_scale
        
        pinch_start_thresh = self.settings.get("pinch_start_threshold", 0.3)
        pinch_release_thresh = self.settings.get("pinch_release_threshold", 0.5)
        
        if self.pinch_state == "OPEN":
            if normalized_pinch < pinch_start_thresh:
                self.pinch_state = "PINCHED"
                self.initial_pinch_dist = raw_pinch_dist
                self.swipe_history.clear()
                return "Pinch", normalized_pinch, "TRACKING", self.debug_data
        elif self.pinch_state == "PINCHED":
            if normalized_pinch > pinch_release_thresh:
                self.pinch_state = "OPEN"
                self.last_action_time = current_time
                if raw_pinch_dist > self.initial_pinch_dist * 1.2:
                    return "Pinch Out", None, "CONFIRMED", self.debug_data
                elif raw_pinch_dist < self.initial_pinch_dist * 0.8:
                    return "Pinch In", None, "CONFIRMED", self.debug_data
            else:
                return "Pinch", normalized_pinch, "TRACKING", self.debug_data

        # 4. Custom ML Fallback
        if self.ml_engine.model is not None:
            history_size = self.settings.get("ml_history_size", 7)
            threshold = self.settings.get("ml_confidence_threshold", 0.85)
            
            if self.prediction_history.maxlen != history_size:
                self.prediction_history = deque(list(self.prediction_history)[-history_size:], maxlen=history_size)
                
            pred_label, confidence = self.ml_engine.predict(landmarks)
            
            self.debug_data["ml_pred"] = pred_label
            self.debug_data["ml_conf"] = round(confidence, 2)
            
            if confidence < threshold:
                pred_label = "UNCERTAIN"
                
            self.prediction_history.append(pred_label)
            
            if len(self.prediction_history) == history_size:
                counts = {}
                for p in self.prediction_history:
                    counts[p] = counts.get(p, 0) + 1
                    
                dominant = max(counts, key=counts.get)
                dom_count = counts[dominant]
                
                # Majority vote
                if dom_count > (history_size / 2):
                    if dominant == "POINTER":
                        return "Pointer", (self.smooth_ptr_x, self.smooth_ptr_y), "TRACKING", self.debug_data
                    elif dominant in ["NEUTRAL", "UNCERTAIN"]:
                        return "None", None, "TRACKING", self.debug_data
                    elif dominant == "NEXT_PAGE":
                        self.last_action_time = current_time
                        self.prediction_history.clear()
                        return "Swipe Left", None, "CONFIRMED", self.debug_data
                    elif dominant == "PREVIOUS_PAGE":
                        self.last_action_time = current_time
                        self.prediction_history.clear()
                        return "Swipe Right", None, "CONFIRMED", self.debug_data
                        
        # 5. Default Fallback
        return "Pointer", (self.smooth_ptr_x, self.smooth_ptr_y), "TRACKING", self.debug_data

    def _detect_pretrained(self, landmarks, canned_gesture, current_time):
        self.debug_data["method"] = "PRETRAINED"
        
        # Strictly use MP gestures
        if canned_gesture == "Pointing_Up":
            return "Pointer", (self.smooth_ptr_x, self.smooth_ptr_y), "TRACKING", self.debug_data
        elif canned_gesture == "Open_Palm":
            # Just an example mapping, user might not want page turning on Open Palm
            return "None", None, "TRACKING", self.debug_data
        elif canned_gesture == "Closed_Fist":
            return "None", None, "TRACKING", self.debug_data
            
        # Still allow dynamic swipe, because Canned doesn't have Swipe
        swipe = self._check_dynamic_swipe(current_time)
        if swipe:
            return swipe, None, "CONFIRMED", self.debug_data
            
        return "Pointer", (self.smooth_ptr_x, self.smooth_ptr_y), "TRACKING", self.debug_data

    def _detect_ml_only(self, landmarks, current_time):
        self.debug_data["method"] = "ML ONLY"
        
        if self.ml_engine.model is None:
            return "None", None, "WAITING", self.debug_data
            
        history_size = self.settings.get("ml_history_size", 7)
        threshold = self.settings.get("ml_confidence_threshold", 0.85)
        
        if self.prediction_history.maxlen != history_size:
            self.prediction_history = deque(list(self.prediction_history)[-history_size:], maxlen=history_size)
            
        pred_label, confidence = self.ml_engine.predict(landmarks)
        
        self.debug_data["ml_pred"] = pred_label
        self.debug_data["ml_conf"] = round(confidence, 2)
        
        if confidence < threshold:
            pred_label = "UNCERTAIN"
            
        self.prediction_history.append(pred_label)
        
        if len(self.prediction_history) == history_size:
            counts = {}
            for p in self.prediction_history:
                counts[p] = counts.get(p, 0) + 1
                
            dominant = max(counts, key=counts.get)
            dom_count = counts[dominant]
            
            if dom_count > (history_size / 2):
                if dominant == "NEXT_PAGE":
                    self.last_action_time = current_time
                    self.prediction_history.clear()
                    return "Swipe Left", None, "CONFIRMED", self.debug_data
                elif dominant == "PREVIOUS_PAGE":
                    self.last_action_time = current_time
                    self.prediction_history.clear()
                    return "Swipe Right", None, "CONFIRMED", self.debug_data
                elif dominant == "ZOOM_IN":
                    self.last_action_time = current_time
                    self.prediction_history.clear()
                    return "Pinch Out", None, "CONFIRMED", self.debug_data
                elif dominant == "ZOOM_OUT":
                    self.last_action_time = current_time
                    self.prediction_history.clear()
                    return "Pinch In", None, "CONFIRMED", self.debug_data
                elif dominant == "POINTER":
                    return "Pointer", (self.smooth_ptr_x, self.smooth_ptr_y), "TRACKING", self.debug_data
                elif dominant in ["NEUTRAL", "UNCERTAIN"]:
                    return "None", None, "TRACKING", self.debug_data
                    
        return "Pointer", (self.smooth_ptr_x, self.smooth_ptr_y), "TRACKING", self.debug_data
