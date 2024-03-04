from PIL import Image, ImageDraw, ImageFont
import argparse
import os
from datetime import datetime

def mm_px(mm):
    return int(mm * 28.3465)

def create_image_with_text(output_file, lines):
    dpi = 360
    width_mm, height_mm = 46, 12
    # width_px = mm_px(34)
    # height_px = mm_px(56)
    width_px = int((width_mm * dpi) / 25.4)
    height_px = int((height_mm * dpi) / 25.4)


    # Create a new white image
    img = Image.new('RGB', (width_px, height_px), 'white')
    draw = ImageDraw.Draw(img)
    # Load the image you want to add
    barcode = Image.open('/home/testbench/io16-testing/Testing/images/barcode.png')
    position = (0, 0)
    img.paste(barcode, position)

    # Define text and position
    number_of_lines = len(lines)
    size = height_px / (number_of_lines )

    font = ImageFont.truetype('DejaVuSansMono', int(size-10))
    font_size = size

    line_height = font_size  # Use font size as line height

    for i, line in enumerate(lines):
        x = 425
        y = i * line_height -2


        # Draw text
        draw.text((x, y), line, (0, 0, 0), font=font)  # Black text

    # Assuming img is your image object
    # gray_img = img.convert('L')  # Convert image to grayscale
    img.save(output_file)


def create_image_without_barcode(output_file, lines):
    dpi = 360
    width_mm, height_mm = 17, 12
    # width_px = mm_px(34)
    # height_px = mm_px(56)
    width_px = int((width_mm * dpi) / 25.4)
    height_px = int((height_mm * dpi) / 25.4)


    # Create a new white image
    img = Image.new('RGB', (width_px, height_px), 'white')
    draw = ImageDraw.Draw(img)

    # Define text and position
    number_of_lines = len(lines)
    size = height_px / (number_of_lines )

    font = ImageFont.truetype('DejaVuSansMono', int(size-10))
    font_size = size

    line_height = font_size  # Use font size as line height

    for i, line in enumerate(lines):
        x = 13
        y = i * line_height -2


        # Draw text
        draw.text((x, y), line, (0, 0, 0), font=font)  # Black text

    # Assuming img is your image object
    # gray_img = img.convert('L')  # Convert image to grayscale
    img.save(output_file)

def main(filename):
    """
    Main function to process the filename.

    Args:
        filename (str): The name of the file to process.
    """
    basename = os.path.basename(filename)
    model, hw, sw = basename.split("_")
    today_date = datetime.today().strftime('%Y/%m/%d')

    lines = [model, hw, sw, today_date]
    print("File details:")
    print(lines)
    # Usage:
    output_file = '/home/testbench/io16-testing/Testing/images/product_label.png'
    create_image_with_text(output_file, lines)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a file.")
    parser.add_argument("filename", help="Name of the file to process")

    args = parser.parse_args()
    main(args.filename)


