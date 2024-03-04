import keyboard
import re, json, os
import logging
from datetime import datetime, timedelta
from termcolor import *

manufacturing_info_file = 'manufacturing_info.json'

# Technician name and manufacturing info to be recorded
technician = ''
hardware_version = ''
batch_id = ''
manufacturing_order = ''
saved_data = None

def format_batch_id(batch):
    global batch_id

    # Define the regex pattern
    regex = r"^(?:\d{2}\d{2}|[0-4]\d-\d{2}-\d{2})$"

    if not re.match(regex, batch) and (len(batch) != 4 or len(batch) != 8):
        print(colored('Batch has to be one of the following formats: YYWW (ex:2320) or YY-MM-DD (ex: 23-07-31)\n', 'white', 'on_red'))
    
    # Check if it's in the "YY-MM-DD" format and convert it
    if len(batch) == 8:
        try:
            date_obj = datetime.strptime(batch, "%y-%m-%d")
            batch = date_obj.strftime('%y%W')
        except ValueError:
            print("Invalid date format in YY-MM-DD.")

    # Check WW is between 01 and 52
    if len(batch) == 4:
        year = int(batch[:2])
        week = int(batch[2:])

    current_year = datetime.now().year % 100  # Get the last 2 digits of the current year

    # range doesnt include the upper limit so we add +1 to it to include the current year
    valid_year_range = range(current_year - 5, current_year + 1)

    if year not in valid_year_range or week < 1 or week > 52:
        print(colored('Batch needs a valid week between 1 and 52, and a year within a 5 year range\n', 'white', 'on_red'))
        return False

    batch_id = batch
    return batch

def get_valid_input(prompt, regex=None):
    global batch_id

    while True:
        user_input = input(colored(prompt, 'white', 'on_blue'))

        if regex and not re.match(regex, user_input):
            if regex == r"^[A-Za-z\s]+$":
                # Name input wrong
                print(colored('Name has to contain spaces and letters only\n', 'white', 'on_red'))
            elif regex == r"^(v?\d{0,2}\.\d{0,2})$":
                # Hardware input wrong
                print(colored('Hardware has to be a number with up to 2 digits and 2 decimals, examples: 1.0 | 15.23\n', 'white', 'on_red'))
            elif regex == r"^(?:\d{2}\d{2}|[0-4]\d-\d{2}-\d{2})$":
                # Date input wrong
                print(colored('Batch has to be one of the following formats: YYWW (ex: 2320) or YY-MM-DD (ex: 23-07-31)\n', 'white', 'on_red'))
            continue
        if regex == r"^(?:\d{2}\d{2}|[0-4]\d-\d{2}-\d{2})$":
            result = format_batch_id(user_input)
            if result is False:
                # Re-enter batch_id for both "YYWW" and "YY-MM-DD" formats
                batch_id = get_valid_input("*** Please enter the batch_id in the form of YYWW (ex:2320) or YY-MM-DD (ex: 23-07-31) and press ENTER ***\n", regex=r"^(?:\d{2}\d{2}|[0-4]\d-\d{2}-\d{2})$")
            else:
                return result
        #check if hardware version has a v
        elif regex == r"^(v?\d{0,2}\.\d{0,2})$":
            return user_input.lstrip('v')  
        return user_input

def current_technician_and_info(saved_technician=None, saved_hardware_version=None, saved_batch_id=None,
                                saved_manufacturing_order=None, variant=None, tested_already = None, test_date = None):
    global technician, hardware_version, batch_id, manufacturing_order, saved_data
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if(test_date == None):
        test_date = current_time
    technician = ''
    hardware_version = ''
    batch_id = ''
    manufacturing_order = ''

    if(tested_already):
        technician = saved_technician
        hardware_version = saved_hardware_version
        batch_id = saved_batch_id
        manufacturing_order = saved_manufacturing_order

    # Load data from JSON
    if(saved_data == None):
        saved_data = load_data_from_json('/home/testbench/io16-testing/Testing/manufacturing_info.json')

    if saved_data and not tested_already:
        timestamp = saved_data.get('timestamp', None)
        if timestamp:
            timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            current_time = datetime.now()
            time_difference = current_time - timestamp
            # Check if the saved data is within the past 30 minutes
            if time_difference < timedelta(minutes=30):
                technician = saved_data.get('technician', '')
                hardware_version = saved_data.get('hardware_version', '')
                batch_id = saved_data.get('batch_id', '')
                manufacturing_order = saved_data.get('manufacturing_order', '')
                # Update the timestamp value
                #saved_data['timestamp'] = current_time.strftime('%Y-%m-%d %H:%M:%S')

                # Save the updated data back to the JSON file
                save_data_to_json('/home/testbench/io16-testing/Testing/manufacturing_info.json', saved_data)
    if(technician != ''):
        print(colored(
            f"Tester: {technician}\nHardware Version: {hardware_version}\nVariant: {variant}\nBatch: {batch_id}\nWork Order: {manufacturing_order}\nTest Date: {test_date}\n",
            'black', 'on_yellow'))
        print(
            colored("*** If the info is still correct, press y. If you need to reenter it, press n ***\n",
                    'white', 'on_blue'))
        while True:
            event = keyboard.read_event(suppress=True)
            if event.event_type == keyboard.KEY_DOWN:
                if event.name == 'y':
                    keyboard.press_and_release('backspace')
                    logging.info(
                        colored(
                            f"Tester: {technician}\nHardware Version: {hardware_version}\nVariant: {variant}\nBatch: {batch_id}\nWork Order: {manufacturing_order}\nTest Date: {test_date}\n",
                            'black', 'on_yellow'))
                   
                    # Save data to JSON
                    save_data_to_json(manufacturing_info_file, {
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'technician': technician,
                        'hardware_version': hardware_version,
                        'batch_id': batch_id,
                        'manufacturing_order': manufacturing_order
                    })
                    
                    return technician, hardware_version, batch_id, manufacturing_order
                elif event.name == 'n':
                    keyboard.press_and_release('backspace')
                    break

    # If no valid saved data or data is not within the past 10 minutes, prompt for user input
    technician = get_valid_input("*** Please enter your name and press ENTER ***\n", regex=r"^[A-Za-z\s]+$").title()
    hardware_version = get_valid_input("*** Please enter the hardware version and press ENTER ***\n",
                                       regex=r"^(v?\d{0,2}\.\d{0,2})$")
    get_valid_input(
        "*** Please enter the batch_id in the form of YYWW (ex:2320) or YY-MM-DD (ex: 23-07-31) and press ENTER ***\n",
        regex=r"^(?:\d{2}\d{2}|[0-4]\d-\d{2}-\d{2})$")
    while True:
        manufacturing_order = get_valid_input(
            "*** Please enter the work order serial and press ENTER ***\n").upper()
        if re.match(r"^MO\d{5}$", manufacturing_order):
            break
        elif re.match(r"^RMA\d{5}$", manufacturing_order):
            break
        else:
            print(
                colored('Work Order should start with "MO" followed by 5 digits (ex: MO00025). \n', 'white',
                        'on_red'))
    logging.info(
        colored(
            f"Tester: {technician}\nHardware Version: {hardware_version}\nVariant: {variant}\nBatch: {batch_id}\nWork Order: {manufacturing_order}\nTest Date: {test_date}\n",
            'black', 'on_yellow'))

    # Save data to JSON
    save_data_to_json(manufacturing_info_file, {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'technician': technician,
        'hardware_version': hardware_version,
        'batch_id': batch_id,
        'manufacturing_order': manufacturing_order
    })

    return technician, hardware_version, batch_id, manufacturing_order

def check_for_failed(filename):
    with open(filename, 'r') as file:
        content = file.readlines()
        for line in content:
            if "Failed" in line:
                return line, True
        return None, False

def save_data_to_json(json_file_path, data= None):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data['timestamp'] = timestamp

    with open(json_file_path, 'w') as json_file:
        json.dump(data, json_file)

def load_data_from_json(json_file_path):
    if os.path.exists(json_file_path):
        with open(json_file_path, 'r') as json_file:
            saved_data = json.load(json_file)
            timestamp_str = saved_data.get('timestamp')

            if timestamp_str:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                current_time = datetime.now()

                # Check if the saved data is within the last 30 minutes
                if current_time - timestamp < timedelta(minutes=30):
                    return saved_data

    return None