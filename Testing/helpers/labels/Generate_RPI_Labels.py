from PIL import Image, ImageDraw, ImageFont
import argparse
import os
from datetime import datetime


def create_image_with_text(output_file, lines):
    dpi = 360
    width_mm, height_mm = 20, 12
    width_px = int((width_mm * dpi) / 25.4)
    height_px = int((height_mm * dpi) / 25.4)

    # Create a new white image
    img = Image.new('RGB', (width_px, height_px), 'white')
    draw = ImageDraw.Draw(img)

    # Load the image you want to add
    image_to_add = Image.open('/home/testbench/rubix-compute-man/images/frog.png')
    position = (width_px-120, 25)
    img.paste(image_to_add, position)

    # Define text and position
    number_of_lines = len(lines)
    size = height_px / (number_of_lines + 1)

    font = ImageFont.truetype('DejaVuSansMono', int(size-10))
    font_size = size

    line_height = font_size  # Use font size as line height

    for i, line in enumerate(lines):
        offset = int(size / 2)
        x = 0 + offset
        y = i * line_height + offset

        # Draw text
        draw.text((x, y), line, (0, 0, 0), font=font)  # Black text

    img.save(output_file)




def main(filename):
    """
    Main function to process the filename.

    Args:
        filename (str): The name of the file to process.
    """
    basename = os.path.basename(filename)
    model_name, version, _ = basename.split("_")
    today_date = datetime.today().strftime('%d/%m/%y')

    lines = [model_name, version, today_date]
    print("File details for label printing:")
    print(lines)
    # Usage:
    output_file = '/home/testbench/rubix-compute-man/images/Flashed_Label.png'
    create_image_with_text(output_file, lines)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a file.")
    parser.add_argument("filename", help="Name of the file to process")

    args = parser.parse_args()
    main(args.filename)


