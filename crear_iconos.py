from PIL import Image, ImageDraw, ImageFont
import os

def crear_icono(size, filename):
    img = Image.new('RGB', (size, size), color='#F97316')
    draw = ImageDraw.Draw(img)
    
    # Círculo blanco en el centro
    margin = size // 4
    draw.ellipse([margin, margin, size-margin, size-margin], 
                 fill='white', outline='white')
    
    # Letra I en el centro
    font_size = size // 3
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    text = "I"
    bbox = draw.textbbox((0,0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    draw.text((x, y), text, fill='#F97316', font=font)
    
    img.save(filename)
    print(f"✓ Creado: {filename}")

os.makedirs('app/static/images', exist_ok=True)
crear_icono(192, 'app/static/images/icon-192.png')
crear_icono(512, 'app/static/images/icon-512.png')
print("¡Íconos creados correctamente!")