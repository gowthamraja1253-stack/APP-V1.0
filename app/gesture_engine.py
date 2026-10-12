import time
import math
from collections import deque
from .ml_engine import MLEngine

class GestureEngine:
    def __init__(self, settings_manager):
        self.settings = settings_manager
        
        # Temporal tracking for swipes (palm center)
        self.swipe_history = deque(maxlen=20)
        
        # Pinch tracking (rolling ratios)
        self.pinch_history = deque(maxlen=10)
        self.pinch_state = "IDLE"  # "OPEN" or "PINCHED"
        
        # ML Engine & temporal history
        self.ml_engine = MLEngine()
        self.prediction_history = deque(maxlen=6)
        
        # Cooldowns
        self.last_action_time = 0
        self.last_pinch_time = 0
        
        # Pointer smoothing
        self.smooth_ptr_x = None
        self.smooth_ptr_y = None
        
        self.debug_data = {}

    def reset_state(self):
        self.swipe_history.clear()
        self.pinch_history.clear()
        self.prediction_history.clear()
        self.pinch_state = "IDLE"
        self.smooth_ptr_x = None
        self.smooth_ptr_y = None

    def _is_pointer_active(self, landmarks, canned_gesture):
        if canned_gesture == "Pointing_Up":
            return True
        if not landmarks or len(landmarks) < 21:
            return False
            
        # Geometric check:
        # Index tip (8) is higher than index PIP (6)
        index_up = landmarks[8][1] < landmarks[6][1]
        
        # Middle (12), Ring (16), Pinky (20) tips lower than their PIP joints
        middle_down = landmarks[12][1] > landmarks[10][1]
        ring_down = landmarks[16][1] > landmarks[14][1]
        pinky_down = landmarks[20][1] > landmarks[18][1]
        
        return index_up and middle_down and ring_down and pinky_down

    def detect_gesture(self, landmarks, handedness="Unknown", frame_width=640, frame_height=480, canned_gesture="None"):
        current_time = time.time()
        
        if not landmarks or len(landmarks) < 21:
            self.reset_state()
            self.debug_data = {"status": "NO HAND"}
            return "None", None, "WAITING", self.debug_data

        # 1. Smooth Pointer Coordinates (Index Tip = 8)
        alpha = self.settings.get("landmark_smoothing_alpha", 0.5)
        raw_x, raw_y = landmarks[8][0], landmarks[8][1]
        if self.smooth_ptr_x is None:
            self.smooth_ptr_x, self.smooth_ptr_y = raw_x, raw_y
        else:
            self.smooth_ptr_x = (alpha * raw_x) + ((1 - alpha) * self.smooth_ptr_x)
            self.smooth_ptr_y = (alpha * raw_y) + ((1 - alpha) * self.smooth_ptr_y)

        # 2. Track Palm Center for Swipes (Average of Wrist=0 and Middle MCP=9)
        palm_x = (landmarks[0][0] + landmarks[9][0]) / 2.0
        palm_y = (landmarks[0][1] + landmarks[9][1]) / 2.0
        self.swipe_history.append((palm_x, palm_y, current_time))

        # Check Pointer State
        is_pointing = self._is_pointer_active(landmarks, canned_gesture)
        
        self.debug_data["canned"] = canned_gesture
        self.debug_data["is_pointing"] = is_pointing
        self.debug_data["hand"] = handedness

        method = self.settings.get("recognition_method", "HYBRID")

        # Cooldown check for discrete actions (page turns, zoom)
        cooldown = self.settings.get("ml_cooldown", 0.6)
        in_cooldown = (current_time - self.last_action_time) < cooldown

        if method == "MEDIA_PIPE_PRETRAINED":
            return self._detect_pretrained(landmarks, canned_gesture, current_time, is_pointing, in_cooldown)
        elif method == "TRAINED MODEL":
            return self._detect_ml_only(landmarks, current_time, is_pointing, in_cooldown)
        elif method == "GEOMETRIC RULES":
            return self._detect_geometric(landmarks, canned_gesture, current_time, is_pointing, in_cooldown)
        else: # "HYBRID" (Default & Recommended)
            return self._detect_hybrid(landmarks, canned_gesture, current_time, is_pointing, in_cooldown)

    def _check_dynamic_swipe(self, current_time):
        if len(self.swipe_history) < 5:
            return None

        # Look back across samples in the window (0.15s to 0.60s ago)
        curr_x, curr_y, curr_t = self.swipe_history[-1]
        
        best_swipe = None
        max_dist = 0
        
        dist_thresh = self.settings.get("swipe_distance_threshold", 0.12)
        dir_ratio = self.settings.get("swipe_direction_ratio", 1.1)

        for past_x, past_y, past_t in reversed(list(self.swipe_history)[:-3]):
            dt = curr_t - past_t
            if dt < 0.12:
                continue
            if dt > 0.65:
                break
                
            dx = curr_x - past_x
            dy = curr_y - past_y
            
            self.debug_data["swipe_dx"] = round(dx, 3)
            self.debug_data["swipe_dy"] = round(dy, 3)

            if abs(dx) > dist_thresh and abs(dx) > abs(dy) * dir_ratio:
                if abs(dx) > max_dist:
                    max_dist = abs(dx)
                    best_swipe = "Swipe Left" if dx < 0 else "Swipe Right"

        if best_swipe:
            self.last_action_time = current_time
            self.swipe_history.clear()
            self.prediction_history.clear()
            return best_swipe

        return None

    def _check_pinch(self, landmarks, canned_gesture, current_time):
        # 1. Canned shortcuts for zoom
        if canned_gesture in ["Thumb_Up", "Victory"]:
            self.last_action_time = current_time
            return "Pinch Out"
        elif canned_gesture in ["Thumb_Down"]:
            self.last_action_time = current_time
            return "Pinch In"

        # 2. Geometric continuous pinch ratio
        wrist = landmarks[0]
        middle_mcp = landmarks[9]
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]

        palm_scale = math.hypot(middle_mcp[0] - wrist[0], middle_mcp[1] - wrist[1])
        if palm_scale < 0.01:
            palm_scale = 0.01

        raw_pinch = math.hypot(index_tip[0] - thumb_tip[0], index_tip[1] - thumb_tip[1])
        ratio = raw_pinch / palm_scale
        
        self.pinch_history.append((ratio, current_time))
        self.debug_data["norm_pinch"] = round(ratio, 2)
        self.debug_data["hand_scale"] = round(palm_scale, 2)

        if len(self.pinch_history) < 4:
            return None

        # Detect transition:
        # Fingers closing from OPEN (> 0.45) to PINCHED (< 0.28) => Pinch In (Zoom Out)
        # Fingers opening from PINCHED (< 0.28) to OPEN (> 0.45) => Pinch Out (Zoom In)
        recent_ratios = [r for r, t in self.pinch_history]
        min_r = min(recent_ratios)
        max_r = max(recent_ratios)
        first_r = recent_ratios[0]
        last_r = recent_ratios[-1]

        if (current_time - self.last_pinch_time) < 0.5:
            return None

        if first_r > 0.42 and last_r < 0.28 and (first_r - last_r) > 0.16:
            self.last_action_time = current_time
            self.last_pinch_time = current_time
            self.pinch_history.clear()
            return "Pinch In"
        elif first_r < 0.28 and last_r > 0.42 and (last_r - first_r) > 0.16:
            self.last_action_time = current_time
            self.last_pinch_time = current_time
            self.pinch_history.clear()
            return "Pinch Out"

        return None

    def _evaluate_ml(self, landmarks, current_time):
        if self.ml_engine.model is None:
            return None

        pred_label, confidence = self.ml_engine.predict(landmarks)
        self.debug_data["ml_pred"] = pred_label
        self.debug_data["ml_conf"] = round(confidence, 2)

        threshold = self.settings.get("ml_confidence_threshold", 0.45)
        if confidence < threshold:
            pred_label = "UNCERTAIN"

        # Canonical mapping
        label_map = {
            "NEXT_PAGE": "Swipe Left",
            "NXT_PAGE": "Swipe Left",
            "PREVIOUS_PAGE": "Swipe Right",
            "PREV_PAGE": "Swipe Right",
            "ZOOM_IN": "Pinch Out",
            "ZOOM_OUT": "Pinch In",
            "POINTER": "Pointer",
            "NEUTRAL": "None"
        }
        mapped_action = label_map.get(pred_label, "UNCERTAIN")
        self.prediction_history.append(mapped_action)

        if len(self.prediction_history) >= 4:
            counts = {}
            for p in self.prediction_history:
                if p not in ["UNCERTAIN", "None"]:
                    counts[p] = counts.get(p, 0) + 1

            if counts:
                dominant = max(counts, key=counts.get)
                if counts[dominant] >= 3:
                    return dominant

        return None

    def _detect_hybrid(self, landmarks, canned_gesture, current_time, is_pointing, in_cooldown):
        self.debug_data["method"] = "HYBRID"

        # Priority 1: If user is pointing, provide pointer tracking smoothly
        if is_pointing:
            self.swipe_history.clear()
            return "Pointer", (self.smooth_ptr_x, self.smooth_ptr_y), "TRACKING", self.debug_data

        # Priority 2: Cooldown check for triggers
        if in_cooldown:
            return "None", None, "TRACKING", self.debug_data

        # Priority 3: Dynamic Swipe Detection
        swipe = self._check_dynamic_swipe(current_time)
        if swipe:
            return swipe, None, "CONFIRMED", self.debug_data

        # Priority 4: Pinch to Zoom
        pinch = self._check_pinch(landmarks, canned_gesture, current_time)
        if pinch:
            return pinch, None, "CONFIRMED", self.debug_data

        # Priority 5: Trained ML Model Trigger
        ml_action = self._evaluate_ml(landmarks, current_time)
        if ml_action and ml_action not in ["Pointer", "None"]:
            self.last_action_time = current_time
            self.prediction_history.clear()
            self.swipe_history.clear()
            return ml_action, None, "CONFIRMED", self.debug_data

        return "None", None, "TRACKING", self.debug_data

    def _detect_geometric(self, landmarks, canned_gesture, current_time, is_pointing, in_cooldown):
        self.debug_data["method"] = "GEOMETRIC"

        if is_pointing:
            self.swipe_history.clear()
            return "Pointer", (self.smooth_ptr_x, self.smooth_ptr_y), "TRACKING", self.debug_data

        if in_cooldown:
            return "None", None, "TRACKING", self.debug_data

        swipe = self._check_dynamic_swipe(current_time)
        if swipe:
            return swipe, None, "CONFIRMED", self.debug_data

        pinch = self._check_pinch(landmarks, canned_gesture, current_time)
        if pinch:
            return pinch, None, "CONFIRMED", self.debug_data

        return "None", None, "TRACKING", self.debug_data

    def _detect_ml_only(self, landmarks, current_time, is_pointing, in_cooldown):
        self.debug_data["method"] = "ML ONLY"

        if is_pointing:
            return "Pointer", (self.smooth_ptr_x, self.smooth_ptr_y), "TRACKING", self.debug_data

        if in_cooldown:
            return "None", None, "TRACKING", self.debug_data

        ml_action = self._evaluate_ml(landmarks, current_time)
        if ml_action:
            if ml_action == "Pointer":
                return "Pointer", (self.smooth_ptr_x, self.smooth_ptr_y), "TRACKING", self.debug_data
            elif ml_action not in ["None", "UNCERTAIN"]:
                self.last_action_time = current_time
                self.prediction_history.clear()
                return ml_action, None, "CONFIRMED", self.debug_data

        # Fallback to swipe in case ML is uncertain
        swipe = self._check_dynamic_swipe(current_time)
        if swipe:
            return swipe, None, "CONFIRMED", self.debug_data

        return "None", None, "TRACKING", self.debug_data

    def _detect_pretrained(self, landmarks, canned_gesture, current_time, is_pointing, in_cooldown):
        self.debug_data["method"] = "PRETRAINED"

        if is_pointing:
            return "Pointer", (self.smooth_ptr_x, self.smooth_ptr_y), "TRACKING", self.debug_data

        if in_cooldown:
            return "None", None, "TRACKING", self.debug_data

        if canned_gesture in ["Thumb_Up", "Victory"]:
            self.last_action_time = current_time
            return "Pinch Out", None, "CONFIRMED", self.debug_data
        elif canned_gesture in ["Thumb_Down"]:
            self.last_action_time = current_time
            return "Pinch In", None, "CONFIRMED", self.debug_data

        swipe = self._check_dynamic_swipe(current_time)
        if swipe:
            return swipe, None, "CONFIRMED", self.debug_data

        return "None", None, "TRACKING", self.debug_data
