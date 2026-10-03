import pymupdf as fitz # PyMuPDF
import os
from PIL import Image

class PDFController:
    def __init__(self):
        self.doc = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom = 1.0
        self.filepath = None
        self.max_zoom = 3.0
        self.min_zoom = 0.5
        
        # Caching for resize optimization
        self.last_target_w = 0
        self.last_target_h = 0
        self.last_zoom = 0
        self.last_page = -1
        self.cached_image = None

    def close(self):
        if self.doc:
            try:
                self.doc.close()
            except:
                pass
            self.doc = None
        self.cached_image = None
        self.last_target_w = 0
        self.last_target_h = 0
        self.last_zoom = 0
        self.last_page = -1

    def open_pdf(self, filepath):
        if not os.path.exists(filepath):
            return False
        self.close()
        try:
            self.doc = fitz.open(filepath)
            self.filepath = filepath
            self.total_pages = len(self.doc)
            self.current_page = 0
            self.zoom = 1.0
            return True
        except Exception as e:
            print(f"Error opening PDF: {e}")
            return False
            
    def get_dimensions(self):
        if self.doc and self.total_pages > 0:
            rect = self.doc.load_page(0).rect
            return int(rect.width), int(rect.height)
        return 0, 0
            
    def get_current_page_image(self, target_width=800, target_height=800):
        if not self.doc:
            return None
            
        # Check cache
        if (self.current_page == self.last_page and 
            self.zoom == self.last_zoom and 
            self.last_target_w == target_width and 
            self.last_target_h == target_height and 
            self.cached_image is not None):
            return self.cached_image
            
        try:
            page = self.doc.load_page(self.current_page)
            
            # Calculate base scale for fit-to-window
            rect = page.rect
            scale_x = target_width / rect.width if rect.width > 0 else 1.0
            scale_y = target_height / rect.height if rect.height > 0 else 1.0
            base_scale = min(scale_x, scale_y)
            
            # Apply zoom on top of base scale
            final_scale = base_scale * self.zoom
            mat = fitz.Matrix(final_scale, final_scale)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            if pix.alpha:
                img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
            else:
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
            self.cached_image = img
            self.last_page = self.current_page
            self.last_zoom = self.zoom
            self.last_target_w = target_width
            self.last_target_h = target_height
            
            return img
        except Exception as e:
            print(f"Error rendering page: {e}")
            return None
        
    def next_page(self):
        if self.doc and self.current_page < self.total_pages - 1:
            self.current_page += 1
            return True
        return False
        
    def prev_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            return True
        return False
        
    def go_to_page(self, page_num):
        if self.doc and 0 <= page_num < self.total_pages:
            self.current_page = page_num
            return True
        return False
        
    def zoom_in(self):
        if self.zoom < self.max_zoom:
            self.zoom = min(self.max_zoom, self.zoom + 0.2)
            return True
        return False
        
    def zoom_out(self):
        if self.zoom > self.min_zoom:
            self.zoom = max(self.min_zoom, self.zoom - 0.2)
            return True
        return False
