import barcode
from barcode.writer import ImageWriter
import os
import random

def generate_barcode_value():
    """Generates a stable unique barcode string like SS-102938"""
    return f"SS-{random.randint(100000, 999999)}"

def create_barcode_image(code, instance_path):
    """
    Generates a PNG image for the given code using Code128.
    Returns path to the generated image.
    """
    barcodes_dir = os.path.join(instance_path, 'barcodes')
    os.makedirs(barcodes_dir, exist_ok=True)
    
    # Python-barcode saves file with extension appended automatically
    filename = f"{code}" 
    filepath = os.path.join(barcodes_dir, filename)
    
    # Use Code128
    rv = barcode.get_barcode_class('code128')
    writer = ImageWriter()
    
    # Render
    generated_path = rv(code, writer=writer).save(filepath)
    return generated_path

def get_barcode_path(code, instance_path):
    """Returns absolute path to barcode image, generating if missing"""
    expected_path = os.path.join(instance_path, 'barcodes', f"{code}.png")
    if not os.path.exists(expected_path):
        return create_barcode_image(code, instance_path)
    return expected_path
