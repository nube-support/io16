import subprocess, helpers.Ssh_Utils as Ssh_Utils, helpers.System_Info as System_Info, helpers.labels.Product_Detail_Labels as Product_Detail_Labels
import helpers.Manufacturing_Info as Manufacturing_Info, helpers.Ssh_Utils as Ssh_Utils, helpers.labels.Generate_Product_Barcode as Generate_Product_Barcode
import sys, json, os, shutil
from termcolor import *
from productsdb import products
from datetime import datetime

FULL_TEST_SUITE = ['Dips_test', 'Modbus_test', 'lora_test', 'UI/IO calib_test', 'UI_raw_test', 'UO_0_10V_test', 'V_in_out_test', 'resistance_test', 'digital_test', 'pulse_test']

with open('configs/io16_prod.json', 'r') as config_file:
    config = json.load(config_file)

products.init_db_path(config["db_path"])
local_test_path = config["local_test_path"]
variant = config["variant"]
make = config["make"]
model = config["model"]
hostname = config["hostname"]
username = config["username"]
password = config["password"]

# Get the directory of the current script and parent
script_directory = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.dirname(script_directory)

# Check if argument not to print has been passed in the terminal
print_flag = ''
if len(sys.argv) > 1 and print_flag == '':
    if sys.argv[1] == '--no-print':
        print_flag = sys.argv[1]

technician, hardware_version, batch_id, manufacturing_order = None, None, None, None

ssh_client = Ssh_Utils.connect_to_rpi(hostname, username, password)

while True:
    # Make sure the test output file is clean for each device
    with open('output.txt', "w") as file:
        file.truncate(0)  

    # Check if technician and info is still the same
    if None not in (technician, hardware_version, batch_id, manufacturing_order):
        technician, hardware_version, batch_id, manufacturing_order = Manufacturing_Info.current_technician_and_info(technician, hardware_version, batch_id, manufacturing_order)
    else:
        # First execution of script, get technician and info
        technician, hardware_version, batch_id, manufacturing_order = Manufacturing_Info.current_technician_and_info()
    
    try:
        # SSH command to execute the Python script on the remote machine
        cmd_ssh = "ssh -i /home/testbench/.ssh/id_rsa pi@192.168.15.111 'sudo python3 /home/pi/Testing/test.py'"
        
        subprocess.run(cmd_ssh, shell=True, check=True)
        print("Test file received succesfully, checking contents...")

        lines = ''
        # Read all lines from the file
        with open("/home/testbench/io16-testing/Testing/output.txt", "r") as file:
            lines = file.readlines()

        unique_id = None
        firmware = None

        # Iterate through all lines in reverse order
        for line in lines:
            if "Unique_ID:" in line and unique_id is None:
                # Extract Unique_ID from the line
                unique_id_start_index = line.find("Unique_ID:") + len("Unique_ID:")
                unique_id = line[unique_id_start_index:].strip()
            if "Firmware:" in line and firmware is None:
                # Extract Firmware from the line
                firmware_start_index = line.find("Firmware:") + len("Firmware:")
                firmware = line[firmware_start_index:].strip()

            # If both values are found, break out of the loop
            if unique_id is not None and firmware is not None:
                break

        print(colored(f'ID: {unique_id}', 'white', 'on_blue'))

        last_line = lines[-1] if lines else ""
        full_test_suit_passed = all(test_case in last_line for test_case in FULL_TEST_SUITE)

        if full_test_suit_passed:
            print(colored('Working - All tests passed succesfully.', 'white', 'on_green'))

            # ADD TO DB

            barcode = ''
            product = products.get_products_by_loraid(unique_id)

            if product:
                barcode = f"{product[0][2]}-{product[0][3]}-{product[0][5]}"

            if(barcode == ''):
                # new product
                barcode = products.add_product(manufacturing_order, make, model, variant, unique_id, 'None', hardware_version, batch_id,
                    firmware, technician, True, ', '.join(FULL_TEST_SUITE))
                print(colored('Product added to database.', 'white', 'on_blue'))

            # barcode found so just update the already existing product in the db
            else:
                barcode = products.update_product(product[0][1], barcode, unique_id, hardware_version, batch_id,
                    firmware, technician, True, ', '.join(FULL_TEST_SUITE))
                print(colored('Existing product information succesfully updated in database.', 'white', 'on_blue'))
    
            # MAKE AND PRINT LABELS
            Generate_Product_Barcode.generate_barcode(barcode)
            today_date = datetime.now().strftime('%Y/%m/%d')
            formated_hw = System_Info.format_hardware_version(hardware_version)
            lines = ["MN:IO-16-N1", f"SW:{firmware}", f"BA:0{formated_hw}{batch_id}", today_date]

            Product_Detail_Labels.create_image_with_text('/home/testbench/io16-testing/Testing/images/product_label.png', lines)
            Product_Detail_Labels.create_image_without_barcode('/home/testbench/io16-testing/Testing/images/text_label.png', lines)

            if print_flag != '--no-print':
                cmd = 'lpr -P PT-P900W -o PageSize=Custom.12x46mm -o Resolution=360dpi -o CutLabel=0 -o ExtraMargin=0mm -o number-up=1 -o orientation-requested=4 -#3 /home/testbench/io16-testing/Testing/images/product_label.png'
                subprocess.check_output(cmd, shell=True, text=True)
                cmd = 'lpr -P PT-P900W -o PageSize=Custom.12x17mm -o Resolution=360dpi -o CutLabel=0 -o ExtraMargin=0mm -o number-up=1 -o orientation-requested=4 -#1 /home/testbench/io16-testing/Testing/images/text_label.png'
                subprocess.check_output(cmd, shell=True, text=True)            
            #Copy test file into the test folder with correct name

            test_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            header_lines = [
            f"Tester: {technician}",
            f"Hardware Version: {hardware_version}",
            f"Variant: {variant}",
            f"Batch: {batch_id}",
            f"Work Order: {manufacturing_order}",
            f"Test Date: {test_date}\n"
            ]
                    
            # Get a list of files in the local directory
            local_files = os.listdir(local_test_path)

            new_filename_path = ''
            barcode_file_count = 0
            # Count files that start with the specified barcode
            barcode_file_count = sum(1 for file in local_files if file.startswith(barcode))

            if(barcode_file_count == 0):
                new_filename_path = f"{barcode}-#1.txt"
            else:
                new_filename_path = f"{barcode}-#{barcode_file_count+1}.txt"

            # Copy the contents of the old file to the new file with added header lines
            with open('/home/testbench/io16-testing/Testing/output.txt', 'r') as old_file, open(os.path.join(local_test_path, new_filename_path), 'w') as new_file:
                # Write header lines at the beginning of the new file
                new_file.write('\n'.join(header_lines))
                
                # Copy the contents of the old file to the new file
                shutil.copyfileobj(old_file, new_file)

        else:
            missing_tests = [test_case for test_case in FULL_TEST_SUITE if test_case not in last_line]
            print(colored(f'Failed - These tests have not passed: {missing_tests}', 'white', 'on_red'))

    except subprocess.CalledProcessError as e:
        print(f"SSH command failed with error: {e}")
        exit(1)
    
    input(colored('Insert new device, press reset button and press enter to execute script. Press Ctrl+c to stop.\n', 'white', 'on_blue'))

