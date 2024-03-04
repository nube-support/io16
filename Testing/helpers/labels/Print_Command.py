from PIL import Image
import subprocess


def print_image(image_path, iteration, printer_name="PT-P900W", resolution=360, cut_label=0, number=1, orientation_requested=4):
    image = Image.open(image_path)
    extra_margin = 0
    height_mm = 12
    width_mm = int(image.width/resolution*25.4)
    number_str = str(number)

    # Ensure there is a margin to prevent incorrect truncation of text after the first image
    if iteration >= 1:
        extra_margin = 1

    # Construct the lpr command
    lpr_command = [
        "lpr",
        "-P", printer_name,
        "-o", f"PageSize=Custom.{height_mm}x{width_mm}mm",
        "-o", f"ExtraMargin={extra_margin}mm",
        f"-#{number_str}",
        image_path
    ]
    print(lpr_command)
    # Execute the lpr command
    subprocess.run(lpr_command)
