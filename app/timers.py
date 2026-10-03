import time

class PresentationTimer:
    def __init__(self):
        self.start_time = 0
        self.elapsed_time = 0
        self.is_running = False

    def start(self):
        if not self.is_running:
            self.start_time = time.time() - self.elapsed_time
            self.is_running = True

    def pause(self):
        if self.is_running:
            self.elapsed_time = time.time() - self.start_time
            self.is_running = False

    def reset(self):
        self.elapsed_time = 0
        if self.is_running:
            self.start_time = time.time()
        else:
            self.start_time = 0

    def get_time_string(self):
        if self.is_running:
            total = time.time() - self.start_time
        else:
            total = self.elapsed_time
        
        hours = int(total // 3600)
        minutes = int((total % 3600) // 60)
        seconds = int(total % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

class PageTimer:
    def __init__(self):
        self.start_time = time.time()

    def reset(self):
        self.start_time = time.time()

    def get_time_string(self):
        total = time.time() - self.start_time
        minutes = int(total // 60)
        seconds = int(total % 60)
        return f"{minutes:02d}:{seconds:02d}"
