import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

class TrainingStudio(ctk.CTkToplevel):
    def __init__(self, master, main_app):
        super().__init__(master)
        self.main_app = main_app
        self.settings = main_app.settings
        self.ml_engine = main_app.gesture_engine.ml_engine
        
        self.title("Gesture Training Studio")
        self.geometry("600x600")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.is_recording = False
        self.current_label = ctk.StringVar(value="NEXT_PAGE")
        self.available_classes = ["NEXT_PAGE", "PREVIOUS_PAGE", "ZOOM_IN", "ZOOM_OUT", "POINTER", "NEUTRAL"]
        
        self.build_ui()
        self.update_stats()
        
    def build_ui(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_record = self.tabview.add("Record")
        self.tab_train = self.tabview.add("Train Model")
        
        # --- Record Tab ---
        ctk.CTkLabel(self.tab_record, text="Select Gesture to Train:", font=("Arial", 16, "bold")).pack(pady=10)
        
        self.class_menu = ctk.CTkOptionMenu(self.tab_record, variable=self.current_label, values=self.available_classes)
        self.class_menu.pack(pady=5)
        
        add_frame = ctk.CTkFrame(self.tab_record, fg_color="transparent")
        add_frame.pack(pady=5)
        self.new_class_entry = ctk.CTkEntry(add_frame, placeholder_text="New Custom Gesture")
        self.new_class_entry.pack(side="left", padx=5)
        ctk.CTkButton(add_frame, text="Add Class", width=80, command=self.add_custom_class).pack(side="left")
        
        self.record_btn = ctk.CTkButton(self.tab_record, text="START RECORDING", fg_color="green", command=self.toggle_recording)
        self.record_btn.pack(pady=20)
        
        self.status_label = ctk.CTkLabel(self.tab_record, text="Waiting...", text_color="yellow")
        self.status_label.pack(pady=5)
        
        self.stats_text = ctk.CTkTextbox(self.tab_record, height=150)
        self.stats_text.pack(fill="x", padx=20, pady=10)
        
        # --- Train Tab ---
        ctk.CTkButton(self.tab_train, text="TRAIN MODEL", height=40, font=("Arial", 16, "bold"), command=self.train_model).pack(pady=20)
        ctk.CTkButton(self.tab_train, text="Clear Entire Dataset", fg_color="red", hover_color="darkred", command=self.clear_dataset).pack(pady=5)
        
        self.train_results = ctk.CTkTextbox(self.tab_train, height=300)
        self.train_results.pack(fill="both", expand=True, padx=20, pady=10)
        
        if self.ml_engine.model:
            self.train_results.insert("1.0", "A trained model is currently loaded.\n\nClasses:\n" + "\n".join(self.ml_engine.classes))

        # --- Test Tab ---
        self.tab_test = self.tabview.add("Test Model")
        ctk.CTkLabel(self.tab_test, text="Live Prediction (Test Mode)", font=("Arial", 16, "bold")).pack(pady=10)
        ctk.CTkLabel(self.tab_test, text="In this mode, PDF actions are disabled. Test your gestures!").pack(pady=5)
        
        self.test_pred_label = ctk.CTkLabel(self.tab_test, text="Prediction: WAITING", font=("Arial", 24))
        self.test_pred_label.pack(pady=20)
        
        self.test_conf_label = ctk.CTkLabel(self.tab_test, text="Confidence: 0%", font=("Arial", 18))
        self.test_conf_label.pack(pady=10)

    def add_custom_class(self):
        new_class = self.new_class_entry.get().strip().upper().replace(" ", "_")
        if new_class and new_class not in self.available_classes:
            self.available_classes.append(new_class)
            self.class_menu.configure(values=self.available_classes)
            self.current_label.set(new_class)
            self.new_class_entry.delete(0, 'end')

    def toggle_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.record_btn.configure(text="STOP RECORDING", fg_color="red")
            self.status_label.configure(text="RECORDING... Make natural movements!", text_color="red")
        else:
            self.is_recording = False
            self.record_btn.configure(text="START RECORDING", fg_color="green")
            self.status_label.configure(text="Waiting...", text_color="yellow")
            
    def process_training_frame(self, landmarks, canned_gesture="None"):
        active_tab = self.tabview.get()
        if active_tab == "Record" and self.is_recording and landmarks:
            label = self.current_label.get()
            success = self.ml_engine.save_sample(label, landmarks)
            if success:
                self.update_stats()
        elif active_tab == "Test Model" and landmarks:
            pred, conf = self.ml_engine.predict(landmarks)
            action_map = {
                "NEXT_PAGE": "Next Page (Flip Forward)",
                "PREVIOUS_PAGE": "Previous Page (Flip Back)",
                "ZOOM_IN": "Zoom In",
                "ZOOM_OUT": "Zoom Out",
                "POINTER": "Pointer Dot",
                "NEUTRAL": "None (Resting)"
            }
            mapped = action_map.get(pred, "None")
            self.test_pred_label.configure(text=f"Prediction: {pred}\nAction: {mapped}")
            self.test_conf_label.configure(text=f"Confidence: {conf*100:.1f}% | Canned: {canned_gesture}")
        elif active_tab == "Test Model" and not landmarks:
            self.test_pred_label.configure(text="Prediction: NO HAND")
            self.test_conf_label.configure(text="Confidence: 0%")

    def update_stats(self):
        stats = self.ml_engine.get_dataset_stats()
        self.stats_text.delete("1.0", "end")
        self.stats_text.insert("1.0", "Dataset Samples:\n")
        total = 0
        for k, v in stats.items():
            self.stats_text.insert("end", f"- {k}: {v}\n")
            total += v
        self.stats_text.insert("end", f"\nTotal Samples: {total}")

    def clear_dataset(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to delete ALL collected data?"):
            self.ml_engine.clear_dataset()
            self.update_stats()
            self.train_results.delete("1.0", "end")
            self.train_results.insert("1.0", "Dataset cleared.")

    def train_model(self):
        self.train_results.delete("1.0", "end")
        self.train_results.insert("1.0", "Training model... please wait.\n")
        self.update()
        
        success, result = self.ml_engine.train_model()
        if success:
            # Automatically activate HYBRID mode so the trained model is active immediately!
            self.settings.set("recognition_method", "HYBRID")
            self.settings.save()
            
            res_str = f"TRAINING COMPLETE & ACTIVATED!\n"
            res_str += f"Current App Mode: HYBRID (Trained Model + Smart Swipes)\n"
            res_str += f"Accuracy: {result['accuracy']*100:.1f}%\n"
            res_str += f"Total Samples: {result['samples']}\n"
            res_str += f"Classes: {', '.join(result['classes'])}\n\n"
            
            if 'recommendations' in result and result['recommendations']:
                res_str += "RECOMMENDATIONS:\n"
                for r in result['recommendations']:
                    res_str += f"- {r}\n"
                res_str += "\n"
                
            self.train_results.insert("end", res_str)
            
            # Show confusion matrix in a popup or new window
            import os
            from PIL import Image
            if os.path.exists(self.ml_engine.cm_path):
                cm_win = ctk.CTkToplevel(self)
                cm_win.title("Confusion Matrix")
                img = Image.open(self.ml_engine.cm_path)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(600, 450))
                lbl = ctk.CTkLabel(cm_win, image=ctk_img, text="")
                lbl.pack(padx=10, pady=10)
                
        else:
            self.train_results.insert("end", f"TRAINING FAILED: {result}")
            
    def on_close(self):
        self.main_app.training_studio = None
        self.destroy()
