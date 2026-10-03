import cv2

class WebcamManager:
    def __init__(self, camera_id=0, width=640, height=480):
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.cap = None

    def __del__(self):
        self.stop()

    def start(self):
        if self.cap:
            self.cap.release()
            
        self.cap = cv2.VideoCapture(self.camera_id)
        if not self.cap.isOpened():
            return False
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        return True

    def set_camera(self, camera_id):
        self.camera_id = camera_id
        return self.start()

    def read_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # Flip horizontally for a mirror-like experience
                return cv2.flip(frame, 1)
        return None

    def stop(self):
        if self.cap:
            self.cap.release()
            self.cap = None
