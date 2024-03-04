import barcode
import argparse
from barcode.writer import ImageWriter

from PIL import Image


def generate_barcode(data):
    barcode_type = barcode.get_barcode_class('code128')  # Using Code 39 format
    bc = barcode_type(data, writer=ImageWriter())
    options = {"module_height": 10, "font_size": 10, "text_distance": 4, "quiet_zone": 0.9, "module_width": 0.18}

    label = bc.render(options)


    width, height = label.size

    left, top, right, bottom = 0, 10, width, height - 29
    label = label.crop((left, top, right, bottom))

    label.save("/home/testbench/io16-testing/Testing/images/barcode_raw.png")

    # Convert mm to pixels
    dpi = 360
    width_px = int((30.3 / 25.4) * dpi)
    height_px = int((12 / 25.4) * dpi)

    # Create blank image
    img = Image.new("RGB", (width_px, height_px), "white")

    # Assuming cropped_img is already defined and has size
    label_width, label_height = label.size

    # Calculate position to center
    x_offset = (width_px - label_width) // 2
    y_offset = (height_px - label_height) // 2

    # Paste cropped_img centered in img
    img.paste(label, (x_offset, y_offset))

    img.save("/home/testbench/io16-testing/Testing/images/barcode.png")


def main():

    parser = argparse.ArgumentParser(description='Generate a barcode.')
    parser.add_argument('data', type=str, help='Data to encode in the barcode')

    args = parser.parse_args()
    data = args.data

    generate_barcode(data)


if __name__ == '__main__':
    main()


