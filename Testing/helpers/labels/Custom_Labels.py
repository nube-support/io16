from PIL import Image, ImageDraw, ImageFont
import argparse
from Print_Command import *
import time

def generate_2d_array(*args):
    # Initialize a list to store the 2D array
    two_d_array = []

    # Iterate through each argument
    for arg in args:
        # Split the argument using the ";" delimiter
        elements = arg.split(";")

        # Add the split elements to the 2D array
        two_d_array.append(elements)

    return two_d_array

def estimate_text_width(text, font):
    # Create a temporary image to render the text
    image = Image.new("RGB", (1, 1), color="white")
    draw = ImageDraw.Draw(image)

    # Estimate the width of the text
    text_width, _ = draw.textsize(text, font)

    return text_width

def split_text(input_text):
    # Split the input text using semicolon as the delimiter
    text_array = input_text.split("; ")

    # Return the resulting array
    return text_array



def generate_label(lines, font_percentage):
    # Set up image properties
    dpi = 360
    font_percentage = font_percentage/100
    # Define text and position
    number_of_lines = len(lines)

    height_px = int((12 / 25.4) * dpi)
    size = height_px / (number_of_lines )
    font = ImageFont.truetype('DejaVuSansMono', int((size-10)*font_percentage))
    index_of_longest_string = max(range(len(lines)), key=lambda i: len(lines[i]))
    width_px = estimate_text_width(lines[index_of_longest_string], font)+20
    
    # Create a blank image
    img = Image.new("RGB",(width_px, height_px), "white")
    draw = ImageDraw.Draw(img)

    line_height = size*font_percentage
    total_height = line_height*number_of_lines
    print(total_height)
    print(height_px)
    y_offset = (height_px - total_height)/2

    for i, line in enumerate(lines):
        offset = int(size / 2)
        x = 10
        y = i * line_height +y_offset


        # Draw text
        draw.text((x, y), line, (0, 0, 0), font=font)  # Black text


    img.save("/home/testbench/io16-testing/Testing/images/output_image.png")

def main():

    # Set up argparse to handle command-line arguments
    parser = argparse.ArgumentParser(description="Process text and generate barcode.")
    parser.add_argument("input_texts", nargs="+", help="Text separated by semicolons")
    parser.add_argument("--number", type=int, default=1, help="Number of copies")
    parser.add_argument("--font_percentage", type=int, default=100, help="Font percentage")
    args = parser.parse_args()

    # Call the generate_2d_array function
    result = generate_2d_array(*args.input_texts)
    iteration = 1
    for row in result:
        print(row)

        # Call the generate_barcode function
        generate_label(row, args.font_percentage)
        print_image(
            "/home/testbench/io16-testing/Testing/images/output_image.png",
            iteration,
            number=args.number
        )

        time.sleep(3)
        iteration += 1
if __name__ == '__main__':
    main()


# example single sticker: python3 Custom_Labels.py "Example Text"
    
# example multiple stickers: python3 Custom_Labels.py "Example Text" "Second Sticker" "Third Sticker"

# cmd = "lpr -P PT-P900W -o PageSize=Custom.12x50mm -o Resolution=360dpi -o CutLabel=0 -o ExtraMargin=1mm -o number-up=1 -o orientation-requested=4 -#1 images/output_image.png"
# subprocess.check_output(cmd, shell=True, text=True)

# TMV-03-MIPU-06-18

# Address: 18

# Dev EUI: 4E75623194339236