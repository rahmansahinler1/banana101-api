from PIL import Image
import io
import base64

class ImageFunctions:
    def __init__(self):
        self.max_size = (300, 300)

    def create_preview(self, image_bytes):
        # Create a smaller, preview version of the image uploaded
        image_data = base64.b64decode(image_bytes)
        image = Image.open(io.BytesIO(image_data))
        image.thumbnail(self.max_size, Image.LANCZOS)
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=85, optimize=True)
        
        return output.getvalue()
    
    def generate_image(self, yourself_image_base64, clothing_image_base64, style):
        pass

