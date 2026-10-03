import customtkinter as ctk
from PIL import Image

class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, settings_manager, apply_callback):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("400x500")
        self.settings = settings_manager
        self.apply_callback = apply_callback
        
        self.grid_columnconfigure(0, weight=1)
        
        # Gesture Settings
        ctk.CTkLabel(self, text="Gesture Settings", font=("Arial", 16, "bold")).pack(pady=(10, 0))
        
        # Pointer style
        self.style_var = ctk.StringVar(value=self.settings.get("pointer_style"))
        ctk.CTkOptionMenu(self, variable=self.style_var, values=["Dot", "Circle", "Crosshair"]).pack(pady=5)
        
        self.trail_var = ctk.BooleanVar(value=self.settings.get("pointer_trail"))
        ctk.CTkSwitch(self, text="Pointer Trail", variable=self.trail_var).pack(pady=5)
        
        self.landmarks_var = ctk.BooleanVar(value=self.settings.get("show_landmarks"))
        ctk.CTkSwitch(self, text="Show Hand Landmarks", variable=self.landmarks_var).pack(pady=5)
        
        ctk.CTkLabel(self, text="Camera Source:").pack()
        self.camera_var = ctk.StringVar(value=str(self.settings.get("camera_id")))
        ctk.CTkOptionMenu(self, variable=self.camera_var, values=["0", "1", "2"]).pack(pady=5)
        
        ctk.CTkLabel(self, text="Recognition Method:").pack()
        self.recog_var = ctk.StringVar(value=self.settings.get("recognition_method"))
        methods = ["HYBRID", "MEDIA_PIPE_PRETRAINED", "TRAINED MODEL", "GEOMETRIC RULES"]
        ctk.CTkOptionMenu(self, variable=self.recog_var, values=methods).pack(pady=5)
        
        self.debug_var = ctk.BooleanVar(value=self.settings.get("debug_mode"))
        ctk.CTkSwitch(self, text="Debug Mode", variable=self.debug_var).pack(pady=5)
        
        ctk.CTkButton(self, text="Save & Apply", command=self.save).pack(pady=20)
        
    def save(self):
        self.settings.set("pointer_style", self.style_var.get())
        self.settings.set("pointer_trail", self.trail_var.get())
        self.settings.set("show_landmarks", self.landmarks_var.get())
        self.settings.set("camera_id", int(self.camera_var.get()))
        self.settings.set("debug_mode", self.debug_var.get())
        self.settings.set("recognition_method", self.recog_var.get())
        self.apply_callback()
        self.destroy()

class HelpDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Gesture Guide")
        self.geometry("300x400")
        
        ctk.CTkLabel(self, text="Gesture Guide", font=("Arial", 20, "bold")).pack(pady=10)
        
        gestures = [
            ("Swipe Left", "Next Page"),
            ("Swipe Right", "Previous Page"),
            ("Pinch In", "Zoom Out"),
            ("Pinch Out", "Zoom In"),
            ("Index Finger", "Pointer")
        ]
        
        for g, d in gestures:
            frame = ctk.CTkFrame(self, fg_color="transparent")
            frame.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(frame, text=g, font=("Arial", 14, "bold")).pack(side="left")
            ctk.CTkLabel(frame, text=d, font=("Arial", 14)).pack(side="right")
            
        ctk.CTkButton(self, text="Close", command=self.destroy).pack(pady=20)

class AppGUI(ctk.CTk):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        
        self.title("Touchless PDF Presentation Controller")
        self.geometry("1400x850")
        
        # Grid config
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # 1. Top Bar
        self.top_bar = ctk.CTkFrame(self, height=50)
        self.top_bar.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=5)
        
        self.file_info_label = ctk.CTkLabel(self.top_bar, text="No PDF Loaded", font=("Arial", 14, "bold"))
        self.file_info_label.pack(side="left", padx=15, pady=10)
        
        self.timer_label = ctk.CTkLabel(self.top_bar, text="00:00:00", font=("Arial", 18, "bold"), text_color="cyan")
        self.timer_label.pack(side="right", padx=15, pady=10)
        
        # 2. Thumbnail Sidebar (Left)
        self.thumb_sidebar = ctk.CTkScrollableFrame(self, width=150)
        self.thumb_sidebar.grid(row=1, column=0, sticky="nswe", padx=(10, 5), pady=5)
        self.thumb_widgets = []
        
        # 3. Main PDF Area (Center)
        self.main_panel = ctk.CTkFrame(self)
        self.main_panel.grid(row=1, column=1, sticky="nswe", padx=5, pady=5)
        self.main_panel.grid_rowconfigure(0, weight=1)
        self.main_panel.grid_columnconfigure(0, weight=1)
        
        self.pdf_canvas = ctk.CTkCanvas(self.main_panel, bg="#1e1e1e", highlightthickness=0)
        self.pdf_canvas.grid(row=0, column=0, sticky="nswe")
        
        self.overview_frame = ctk.CTkScrollableFrame(self.main_panel, fg_color="#1e1e1e")
        # Hidden by default
        
        # 4. Right Sidebar (Controls & Webcam)
        self.right_sidebar = ctk.CTkFrame(self, width=320)
        self.right_sidebar.grid(row=1, column=2, sticky="nswe", padx=(5, 10), pady=5)
        self.right_sidebar.grid_propagate(False)
        
        # Webcam
        self.webcam_label = ctk.CTkLabel(self.right_sidebar, text="Camera Off", width=300, height=225, fg_color="black")
        self.webcam_label.pack(pady=10, padx=10)
        
        # Status
        self.status_frame = ctk.CTkFrame(self.right_sidebar)
        self.status_frame.pack(fill="x", padx=10, pady=5)
        
        self.gesture_status = ctk.CTkLabel(self.status_frame, text="Gesture: None\nStatus: WAITING", justify="left")
        self.gesture_status.pack(pady=5, anchor="w", padx=10)
        
        self.page_status = ctk.CTkLabel(self.status_frame, text="Page: 0 / 0 | Zoom: 100%")
        self.page_status.pack(pady=5, anchor="w", padx=10)
        
        # Controls Group
        self.controls_frame = ctk.CTkScrollableFrame(self.right_sidebar)
        self.controls_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        ctk.CTkButton(self.controls_frame, text="Open PDF", command=self.main_app.on_open_pdf).pack(fill="x", pady=5)
        ctk.CTkButton(self.controls_frame, text="Toggle Camera", command=self.main_app.toggle_camera).pack(fill="x", pady=5)
        ctk.CTkButton(self.controls_frame, text="Train Gestures", fg_color="purple", hover_color="indigo", command=self.main_app.open_training_studio).pack(fill="x", pady=5)
        ctk.CTkButton(self.controls_frame, text="Overview Mode", command=self.main_app.toggle_overview).pack(fill="x", pady=5)
        
        nav_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        nav_frame.pack(fill="x", pady=5)
        ctk.CTkButton(nav_frame, text="Prev", width=130, command=self.main_app.on_prev_page).pack(side="left")
        ctk.CTkButton(nav_frame, text="Next", width=130, command=self.main_app.on_next_page).pack(side="right")
        
        jump_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        jump_frame.pack(fill="x", pady=5)
        self.jump_entry = ctk.CTkEntry(jump_frame, placeholder_text="Go to Page...", width=130)
        self.jump_entry.pack(side="left")
        ctk.CTkButton(jump_frame, text="Go", width=60, command=self.main_app.on_jump_page).pack(side="left", padx=5)
        
        zoom_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        zoom_frame.pack(fill="x", pady=5)
        ctk.CTkButton(zoom_frame, text="Zoom Out", width=130, command=self.main_app.on_zoom_out).pack(side="left")
        ctk.CTkButton(zoom_frame, text="Zoom In", width=130, command=self.main_app.on_zoom_in).pack(side="right")
        
        ctk.CTkButton(self.controls_frame, text="Presentation Mode (F11)", command=self.main_app.toggle_presentation_mode, fg_color="purple").pack(fill="x", pady=10)
        
        self.mode_var = ctk.StringVar(value="Gesture")
        ctk.CTkSwitch(self.controls_frame, text="Gesture Mode", variable=self.mode_var, onvalue="Gesture", offvalue="Manual", command=self.main_app.on_mode_change).pack(pady=10)
        
        ctk.CTkButton(self.controls_frame, text="Demo Mode", command=self.main_app.enable_demo_mode, fg_color="#ff8c00").pack(fill="x", pady=5)
        
        # Timers
        timer_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        timer_frame.pack(fill="x", pady=5)
        ctk.CTkButton(timer_frame, text="Start/Pause Timer", command=self.main_app.toggle_timer).pack(fill="x", pady=2)
        ctk.CTkButton(timer_frame, text="Reset Timer", command=self.main_app.reset_timer).pack(fill="x", pady=2)
        
        ctk.CTkButton(self.controls_frame, text="Gesture Help", command=self.show_help).pack(fill="x", pady=5)
        ctk.CTkButton(self.controls_frame, text="Settings", command=self.show_settings).pack(fill="x", pady=5)
        ctk.CTkButton(self.controls_frame, text="System Check", command=self.main_app.system_check).pack(fill="x", pady=5)
        
        self.recent_frame = ctk.CTkFrame(self.controls_frame)
        self.recent_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(self.recent_frame, text="Recent PDFs", font=("Arial", 12, "bold")).pack(pady=2)
        self.recent_buttons = []
        
        # State
        self.pdf_image_id = None
        self.current_tk_image = None
        self.pointer_id = None
        self.trail_ids = []
        self.overview_images = []
        
    def populate_overview(self, thumbnails, click_callback):
        # Clear existing
        for widget in self.overview_frame.winfo_children():
            widget.destroy()
        self.overview_images.clear()
        
        columns = 4
        from PIL import ImageTk
        for i, img in enumerate(thumbnails):
            if img:
                tk_img = ImageTk.PhotoImage(img.resize((150, 200), Image.Resampling.LANCZOS))
                self.overview_images.append(tk_img)
                lbl = ctk.CTkLabel(self.overview_frame, image=tk_img, text=f"Page {i+1}", compound="top", cursor="hand2")
                lbl.grid(row=i // columns, column=i % columns, padx=10, pady=10)
                lbl.bind("<Button-1>", lambda e, p=i: click_callback(p))

    def show_overview(self):
        self.pdf_canvas.grid_remove()
        self.overview_frame.grid(row=0, column=0, sticky="nswe")

    def hide_overview(self):
        self.overview_frame.grid_remove()
        self.pdf_canvas.grid(row=0, column=0, sticky="nswe")
        
    def show_settings(self):
        SettingsDialog(self, self.main_app.settings, self.main_app.apply_settings)
        
    def show_help(self):
        HelpDialog(self)

    def update_recent_files(self, paths):
        for btn in self.recent_buttons:
            btn.destroy()
        self.recent_buttons.clear()
        
        for p in paths:
            name = p.split("/")[-1]
            btn = ctk.CTkButton(self.recent_frame, text=name, anchor="w", fg_color="transparent", 
                                command=lambda path=p: self.main_app.open_recent(path))
            btn.pack(fill="x", padx=5, pady=1)
            self.recent_buttons.append(btn)

    def populate_thumbnails(self, num_pages):
        for w in self.thumb_widgets:
            w.destroy()
        self.thumb_widgets.clear()
        
        for i in range(num_pages):
            lbl = ctk.CTkLabel(self.thumb_sidebar, text=f"Page {i+1}", cursor="hand2")
            lbl.pack(pady=5)
            lbl.bind("<Button-1>", lambda e, p=i: self.main_app.on_thumb_click(p))
            self.thumb_widgets.append(lbl)

    def set_thumbnail_image(self, page_num, img):
        if page_num < len(self.thumb_widgets):
            from PIL import ImageTk
            tk_img = ImageTk.PhotoImage(img)
            self.thumb_widgets[page_num].configure(image=tk_img, text="")
            self.thumb_widgets[page_num].image = tk_img # Keep ref

    def highlight_thumbnail(self, page_num):
        for i, lbl in enumerate(self.thumb_widgets):
            if i == page_num:
                lbl.configure(fg_color="#3a7ebf")
            else:
                lbl.configure(fg_color="transparent")

    def update_webcam(self, image):
        if image:
            image = image.resize((300, 225), Image.Resampling.LANCZOS)
            self._current_webcam_img = ctk.CTkImage(light_image=image, dark_image=image, size=(300, 225))
            self.webcam_label.configure(image=self._current_webcam_img, text="")
        else:
            self._current_webcam_img = None
            try:
                self.webcam_label.configure(image="", text="Camera Off")
            except Exception:
                pass
        
    def update_pdf(self, image):
        from PIL import ImageTk
        self.current_tk_image = ImageTk.PhotoImage(image)
        c_width = self.pdf_canvas.winfo_width()
        c_height = self.pdf_canvas.winfo_height()
        
        x = max(0, (c_width - image.width) // 2)
        y = max(0, (c_height - image.height) // 2)
        
        if self.pdf_image_id is None:
            self.pdf_image_id = self.pdf_canvas.create_image(x, y, anchor="nw", image=self.current_tk_image)
        else:
            self.pdf_canvas.coords(self.pdf_image_id, x, y)
            self.pdf_canvas.itemconfig(self.pdf_image_id, image=self.current_tk_image)
            
    def update_pointer(self, x_ratio, y_ratio, style="Dot", size=8, add_trail=False):
        c_width = self.pdf_canvas.winfo_width()
        c_height = self.pdf_canvas.winfo_height()
        
        if c_width <= 1 or c_height <= 1: return
            
        x = x_ratio * c_width
        y = y_ratio * c_height
        
        r = size
        color = "red"
        
        # Trail logic
        if add_trail:
            tid = self.pdf_canvas.create_oval(x-2, y-2, x+2, y+2, fill="orange", outline="")
            self.trail_ids.append(tid)
            if len(self.trail_ids) > 15:
                old = self.trail_ids.pop(0)
                self.pdf_canvas.delete(old)
        else:
            for tid in self.trail_ids:
                self.pdf_canvas.delete(tid)
            self.trail_ids.clear()
        
        if self.pointer_id is not None:
            self.pdf_canvas.delete(self.pointer_id)
            
        if style == "Dot":
            self.pointer_id = self.pdf_canvas.create_oval(x-r, y-r, x+r, y+r, fill=color, outline="white")
        elif style == "Circle":
            self.pointer_id = self.pdf_canvas.create_oval(x-r, y-r, x+r, y+r, fill="", outline=color, width=2)
        elif style == "Crosshair":
            self.pointer_id = self.pdf_canvas.create_line(x-r, y, x+r, y, fill=color, width=2)
            cross2 = self.pdf_canvas.create_line(x, y-r, x, y+r, fill=color, width=2)
            # grouped logically
            
    def hide_pointer(self):
        if self.pointer_id is not None:
            self.pdf_canvas.delete(self.pointer_id)
            self.pointer_id = None
            
    def show_notification(self, text):
        c_width = self.pdf_canvas.winfo_width()
        c_height = self.pdf_canvas.winfo_height()
        notif_id = self.pdf_canvas.create_text(c_width/2, c_height - 50, text=text, font=("Arial", 30, "bold"), fill="yellow")
        self.after(1500, lambda: self.pdf_canvas.delete(notif_id))

    def toggle_presentation_ui(self, is_presentation):
        if is_presentation:
            self.top_bar.grid_remove()
            self.thumb_sidebar.grid_remove()
            self.right_sidebar.grid_remove()
        else:
            self.top_bar.grid()
            self.thumb_sidebar.grid()
            self.right_sidebar.grid()
