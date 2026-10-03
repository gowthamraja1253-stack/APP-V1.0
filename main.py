import sys
import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
import cv2

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.gui import AppGUI
from app.pdf_controller import PDFController
from app.hand_tracker import HandTracker
from app.gesture_engine import GestureEngine
from app.webcam import WebcamManager
from app.settings import SettingsManager
from app.timers import PresentationTimer, PageTimer
from app.thumbnail_manager import ThumbnailManager
from app.gui_training import TrainingStudio

class MainApp:
    def __init__(self):
        self.training_studio = None
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        self.settings = SettingsManager()
        self.pdf_controller = PDFController()
        self.thumbnail_manager = ThumbnailManager()
        
        self.hand_tracker = HandTracker()
        self.gesture_engine = GestureEngine(self.settings)
        self.webcam = WebcamManager(camera_id=self.settings.get("camera_id"))
        
        self.presentation_timer = PresentationTimer()
        self.page_timer = PageTimer()
        
        self.gui = AppGUI(self)
        
        self.is_gesture_mode = True
        self.is_running = True
        self.is_camera_active = False
        self.is_fullscreen = False
        self.is_presentation_mode = False
        
        self.gui.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Key bindings
        self.gui.bind("<Left>", lambda e: self.on_prev_page())
        self.gui.bind("<Right>", lambda e: self.on_next_page())
        self.gui.bind("<plus>", lambda e: self.on_zoom_in())
        self.gui.bind("<minus>", lambda e: self.on_zoom_out())
        self.gui.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.gui.bind("<Escape>", lambda e: self.exit_fullscreen())
        self.gui.bind("<space>", lambda e: self.toggle_presentation_mode())
        
        self.gui.update_recent_files(self.settings.get("recent_pdfs"))
        
        if self.settings.get("show_gesture_guide"):
            self.gui.show_help()
            
        self.on_start_camera()
        self.gui.after(30, self.update_loop)
        self.gui.after(1000, self.timer_loop)
        
        self.gui.mainloop()

    def apply_settings(self):
        # Restart camera if changed
        new_cam = self.settings.get("camera_id")
        if new_cam != self.webcam.camera_id:
            if self.is_camera_active:
                self.webcam.stop()
            self.webcam.set_camera(new_cam)
            if self.is_camera_active:
                self.webcam.start()
                
    def open_recent(self, path):
        if self.pdf_controller.open_pdf(path):
            self.on_pdf_opened(path)
        else:
            messagebox.showerror("Error", f"Could not open {path}")

    def on_open_pdf(self):
        filepath = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if filepath:
            if self.pdf_controller.open_pdf(filepath):
                self.settings.add_recent_pdf(filepath)
                self.gui.update_recent_files(self.settings.get("recent_pdfs"))
                self.on_pdf_opened(filepath)

    def on_pdf_opened(self, filepath):
        self.thumbnail_manager.set_document(self.pdf_controller.doc)
        
        w, h = self.pdf_controller.get_dimensions()
        filename = os.path.basename(filepath)
        self.gui.file_info_label.configure(text=f"{filename} | {w}x{h} px | {self.pdf_controller.total_pages} Pages")
        
        self.gui.populate_thumbnails(self.pdf_controller.total_pages)
        self.update_pdf_view()
        
        # Async thumbnail generation
        self.gui.after(100, self.generate_next_thumbnail, 0)
        
    def generate_next_thumbnail(self, page_num):
        if page_num < self.pdf_controller.total_pages:
            img = self.thumbnail_manager.get_thumbnail(page_num)
            if img:
                self.gui.set_thumbnail_image(page_num, img)
            self.gui.after(10, self.generate_next_thumbnail, page_num + 1)

    def on_thumb_click(self, page_num):
        if self.pdf_controller.go_to_page(page_num):
            self.page_timer.reset()
            self.update_pdf_view()
            self.gui.hide_overview()
            
    def on_jump_page(self):
        try:
            val = int(self.gui.jump_entry.get()) - 1
            if self.pdf_controller.go_to_page(val):
                self.page_timer.reset()
                self.update_pdf_view()
        except:
            pass
        self.gui.jump_entry.delete(0, "end")

    def update_pdf_view(self):
        w = self.gui.pdf_canvas.winfo_width()
        h = self.gui.pdf_canvas.winfo_height()
        if w < 100: w = 800
        if h < 100: h = 800
        
        img = self.pdf_controller.get_current_page_image(target_width=w, target_height=h)
        if img:
            self.gui.update_pdf(img)
            self.gui.page_status.configure(text=f"Page: {self.pdf_controller.current_page + 1} / {self.pdf_controller.total_pages} | Zoom: {int(self.pdf_controller.zoom * 100)}%")
            self.gui.highlight_thumbnail(self.pdf_controller.current_page)

    def on_next_page(self):
        if self.pdf_controller.next_page():
            self.page_timer.reset()
            self.gui.show_notification(f"NEXT PAGE: {self.pdf_controller.current_page+1}")
            self.update_pdf_view()

    def on_prev_page(self):
        if self.pdf_controller.prev_page():
            self.page_timer.reset()
            self.gui.show_notification(f"PREV PAGE: {self.pdf_controller.current_page+1}")
            self.update_pdf_view()
            
    def on_zoom_in(self):
        if self.pdf_controller.zoom_in():
            self.gui.show_notification(f"ZOOM IN: {int(self.pdf_controller.zoom*100)}%")
            self.update_pdf_view()
            
    def on_zoom_out(self):
        if self.pdf_controller.zoom_out():
            self.gui.show_notification(f"ZOOM OUT: {int(self.pdf_controller.zoom*100)}%")
            self.update_pdf_view()

    def on_start_camera(self):
        if not self.is_camera_active:
            if self.webcam.start():
                self.is_camera_active = True
                self.gui.gesture_status.configure(text="Gesture: None\nStatus: WAITING")
            else:
                self.gui.gesture_status.configure(text="Camera Error")

    def on_stop_camera(self):
        if self.is_camera_active:
            self.webcam.stop()
            self.is_camera_active = False
            self.gui.update_webcam(None)
            self.gui.gesture_status.configure(text="Camera Off")
            
    def toggle_camera(self):
        if self.is_camera_active:
            self.on_stop_camera()
        else:
            self.on_start_camera()
            
    def open_training_studio(self):
        if self.training_studio is None or not self.training_studio.winfo_exists():
            self.training_studio = TrainingStudio(self.gui, self)
        self.training_studio.focus()

    def update_loop(self):
        if not self.is_running:
            return
            
        if self.is_camera_active:
            frame = self.webcam.read_frame()
            if frame is not None:
                h, w, _ = frame.shape
                draw = self.settings.get("show_landmarks")
                processed_frame, landmarks, handedness, canned_gesture = self.hand_tracker.process_frame(frame, draw_landmarks=draw)
                
                if self.training_studio and self.training_studio.winfo_exists():
                    self.training_studio.process_training_frame(landmarks, canned_gesture)
                
                if self.is_gesture_mode:
                    gesture, data, status, debug_data = self.gesture_engine.detect_gesture(landmarks, handedness, w, h, canned_gesture)
                    
                    if status == "CONFIRMED":
                        self.handle_gesture(gesture, data)
                        
                    self.gui.gesture_status.configure(text=f"Gesture: {gesture}\nStatus: {status}")
                    
                    if self.settings.get("debug_mode"):
                        dbg_text = f"DEBUG MODE\nHand: {handedness}\nScale: {debug_data.get('hand_scale', 0)}\nPinch: {debug_data.get('norm_pinch', 0)}\ndx: {debug_data.get('swipe_dx', 0)}\nCanned: {canned_gesture}"
                        self.gui.file_info_label.configure(text=dbg_text, text_color="yellow")
                    else:
                        # Restore normal top bar if it was in debug mode
                        if "DEBUG MODE" in self.gui.file_info_label.cget("text"):
                            file_w, file_h = self.pdf_controller.get_dimensions()
                            filename = os.path.basename(self.pdf_controller.filepath) if self.pdf_controller.filepath else "No PDF"
                            self.gui.file_info_label.configure(text=f"{filename} | {file_w}x{file_h} px | {self.pdf_controller.total_pages} Pages", text_color="white")
                    
                    if gesture == "Pointer" and data is not None:
                        style = self.settings.get("pointer_style")
                        size = self.settings.get("pointer_size")
                        trail = self.settings.get("pointer_trail")
                        self.gui.update_pointer(data[0], data[1], style, size, trail)
                    else:
                        self.gui.hide_pointer()
                else:
                    self.gui.gesture_status.configure(text="Gesture Mode: OFF\nStatus: WAITING")
                    self.gui.hide_pointer()
                
                # Convert back to PIL Image and show
                import cv2
                rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_frame)
                self.gui.update_webcam(pil_img)
            else:
                self.on_stop_camera()
                
        self.gui.after(30, self.update_loop)

    def handle_gesture(self, gesture, data):
        if gesture == "Swipe Left":
            self.on_next_page()
        elif gesture == "Swipe Right":
            self.on_prev_page()
        elif gesture == "Pinch In":
            self.on_zoom_out()
        elif gesture == "Pinch Out":
            self.on_zoom_in()

    def timer_loop(self):
        if not self.is_running: return
        p_time = self.presentation_timer.get_time_string()
        if self.settings.get("page_timer"):
            pg_time = self.page_timer.get_time_string()
            self.gui.timer_label.configure(text=f"{p_time} | Page: {pg_time}")
        else:
            self.gui.timer_label.configure(text=p_time)
        self.gui.after(1000, self.timer_loop)

    def toggle_timer(self):
        if self.presentation_timer.is_running:
            self.presentation_timer.pause()
        else:
            self.presentation_timer.start()

    def reset_timer(self):
        self.presentation_timer.reset()
        self.page_timer.reset()

    def toggle_presentation_mode(self):
        self.is_presentation_mode = not self.is_presentation_mode
        self.gui.toggle_presentation_ui(self.is_presentation_mode)
        self.gui.after(100, self.update_pdf_view)

    def toggle_overview(self):
        # Only populate if not currently showing
        if not self.gui.overview_frame.winfo_ismapped():
            # Get all thumbnails from cache
            thumbnails = [self.thumbnail_manager.get_thumbnail(i) for i in range(self.pdf_controller.total_pages)]
            self.gui.populate_overview(thumbnails, self.on_thumb_click)
            self.gui.show_overview()
        else:
            self.gui.hide_overview()

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.gui.attributes("-fullscreen", self.is_fullscreen)
        self.gui.after(100, self.update_pdf_view)

    def exit_fullscreen(self):
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.gui.attributes("-fullscreen", False)
            self.gui.after(100, self.update_pdf_view)

    def on_mode_change(self):
        self.is_gesture_mode = (self.gui.mode_var.get() == "Gesture")

    def enable_demo_mode(self):
        # Open a clean presentation layout, gesture guide, toggle gesture mode on.
        self.gui.mode_var.set("Gesture")
        self.is_gesture_mode = True
        self.gui.show_help()
        self.is_presentation_mode = True
        self.gui.toggle_presentation_ui(True)
        self.gui.attributes("-fullscreen", True)
        self.is_fullscreen = True
        self.gui.after(100, self.update_pdf_view)
        
    def system_check(self):
        try:
            import cv2
            import mediapipe
            import pymupdf
            import numpy
            import customtkinter
            import PIL
            
            cam_status = "Available"
            if not self.is_camera_active:
                test_cap = cv2.VideoCapture(self.settings.get("camera_id"))
                if not test_cap.isOpened():
                    cam_status = "Failed to open camera"
                test_cap.release()
                
            messagebox.showinfo("System Check", f"SYSTEM READY\n\nAll core packages loaded successfully.\nCamera Status: {cam_status}")
        except Exception as e:
            messagebox.showerror("System Check Failed", f"SYSTEM CHECK FAILED\n\nError: {e}")

    def on_closing(self):
        self.is_running = False
        self.on_stop_camera()
        self.pdf_controller.close()
        self.thumbnail_manager.clear()
        self.gui.destroy()

if __name__ == "__main__":
    MainApp()
