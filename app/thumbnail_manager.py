import pymupdf as fitz
from PIL import Image

class ThumbnailManager:
    def __init__(self):
        self.cache = {}
        self.doc = None

    def set_document(self, doc):
        self.doc = doc
        self.cache.clear()

    def get_thumbnail(self, page_num, width=150):
        if not self.doc:
            return None
            
        if page_num in self.cache:
            return self.cache[page_num]

        try:
            page = self.doc.load_page(page_num)
            rect = page.rect
            scale = width / rect.width if rect.width > 0 else 0.5
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat)
            
            if pix.alpha:
                img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
            else:
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
            self.cache[page_num] = img
            return img
        except Exception as e:
            print(f"Failed to generate thumbnail for page {page_num}: {e}")
            return None

    def clear(self):
        self.cache.clear()
        self.doc = None
