import re, json
import logging
from termcolor import *
import keyboard, time, threading
import helpers.Ssh_Utils as Ssh_Utils, subprocess

def format_hardware_version(hardware_version):
    # Split the version number into major and minor parts
    major, _, minor = hardware_version.partition('.')

    # Add a zero to the minor part if it has only one digit
    minor = minor.ljust(2, '0')

    # Combine major and minor parts, remove the decimal point, and convert to an integer
    formatted_version = int(major + minor)

    return formatted_version

def kernel_software_version(ssh_client):
    stdin, stdout, stderr = ssh_client.exec_command('uname -r')
    output = stdout.read().decode('utf-8').strip().split('\n')
    # Join the list elements into a single string
    output_str = '\n'.join(output)

    # Remove extra spaces and trailing commas to make it valid JSON
    kerner_version = output_str.replace('    ', '').replace(',', '').strip()

    if output:
        logging.info(colored(f"Kernel version: {kerner_version}", 'white', 'on_blue'))
    else:
        logging.info(colored(f"Failed - Kernel version not found.\n", 'white', 'on_red'))
    return kerner_version

def append_key_value_to_json(ssh_client, key, value, remote_path):
    # Read the JSON file content over SSH
    stdin, stdout, stderr = ssh_client.exec_command(f'cat {remote_path}')
    json_data = stdout.read().decode('utf-8')

    # Parse the JSON data
    data = json.loads(json_data)

    # Append the key-value pair
    data[key] = value

    # Serialize the updated data to JSON format
    updated_json_data = json.dumps(data, indent=4)

    # Write the updated JSON data back to the file over SSH
    with ssh_client.open_sftp().file(remote_path, 'w') as file:
        file.write(updated_json_data)

def check_product_json_for_barcode(ssh_client):
    remote_path = '/data/product.json'
    try:
        # Read the JSON file content over SSH
        stdin, stdout, stderr = ssh_client.exec_command(f'cat {remote_path}')
        json_data = stdout.read().decode('utf-8')

        # Parse the JSON data
        data = json.loads(json_data)

        # Check if 'serial_number' key exists in the JSON data
        barcode = data.get('serial_number', '')

        return barcode
    except Exception as e:
        print(f"An error occurred: {e}")
        return ''

def change_MAC_address(ssh_client):
    stdin, stdout, stderr = ssh_client.exec_command('cd /home/pi/rubix-scripts/utility/MAC_tool && python MAC_tool.py')
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    comments = ''
    if output.count('complete') == 3:
        logging.info(colored("Mac address change complete.", 'white', 'on_green'))
        comments = 'Reset MAC'
    else:
        logging.info(colored("Mac address change incomplete.", 'white', 'on_red'))
    
    if error:
        logging.info(colored(f"Mac address change incomplete, error: {error}.", 'white', 'on_red'))

    mac_address_match = re.search(r'Generated MAC Address: (\S+)', output)
    if mac_address_match:
        mac_address = mac_address_match.group(1)
        logging.info(colored(f"Generated MAC Address: {mac_address}", 'white', 'on_green'))
    else:
        logging.info(colored("Unable to extract MAC address from output.", 'white', 'on_red'))
    return comments 
def check_if_directory_exists(ssh_client, directory_path):
    try:
        # Use SFTP to list the directory content
        sftp = ssh_client.open_sftp()
        sftp.listdir(directory_path)
        sftp.close()
        return True
    except IOError:
        return False
    
def rc_software_version(ssh_client, should_log = None):
    stdin, stdout, stderr = ssh_client.exec_command('cat /data/product.json')
    output = stdout.read().decode('utf-8').strip().split('\n')
    # Join the list elements into a single string
    output_str = ''.join(output)
    
    # Extract the version using regular expressions
    import re
    version_match = re.search(r'"version": "v(.*?)"', output_str)

    if version_match:
        version = version_match.group(1).lstrip('v')  # Remove 'v' from the beginning
        if should_log:
            logging.info(colored(f"RC software version: {version}", 'white', 'on_blue'))
        return version
    else:
        if should_log:
            logging.info(colored(f"Failed - RC software version not found.\n", 'white', 'on_red'))
        return 'No RC version found'

def log_harddrive_info(ssh_client):
    total_size_gb = 0.0
    total_avail_gb = 0.0
    total_used_gb = 0.0

    cmd = "df -h --output=source,size,avail,used"
    stdin, stdout, stderr = ssh_client.exec_command('df -h -P')
    result = stdout.read().decode('utf-8')

    lines = result.split('\n')[1:-1]  # Skip the header and last empty line
    total_avail_gb = 0
    size_string = re.split(r'\s+', lines[0].strip())[3].strip()

    if 'G' in size_string:
        total_avail_gb = float(size_string.strip('G'))
    elif 'M' in size_string:
        total_avail_gb = float(size_string.strip('M')) / 1000

    for line in lines:
        columns = re.split(r'\s+', line.strip())
        size = columns[1]


        # Convert sizes, available, and used to GB
        if size.endswith('M'):
            total_size_gb += float(size[:-1]) / 1024
        elif size.endswith('G'):
            total_size_gb += float(size[:-1])


    # Truncate the values to two decimal places
    total_size_gb = round(total_size_gb)
    total_avail_gb = round(total_avail_gb, 2)
    total_used_gb = total_size_gb - total_avail_gb

    logging.info(colored(f"Total Size: {total_size_gb:.2f} GB\nTotal Used: {total_used_gb:.2f} GB\nTotal Available: {total_avail_gb:.2f} GB\n", 'white', 'on_blue'))
    
    return result

def log_memory_info(ssh_client):
    stdin, stdout, stderr = ssh_client.exec_command('cat /proc/meminfo')
    output = stdout.read().decode('utf-8')
    memory_info = {}

    for line in output.split('\n'):
        parts = line.split(':')
        if len(parts) == 2:
            key = parts[0].strip()
            value = parts[1].strip()
            memory_info[key] = value

    total_memory_kb = int(memory_info.get('MemTotal', '0').split()[0])

    total_memory_mb = total_memory_kb / 1024

    logging.info(colored(f"Total Memory: {total_memory_mb:.2f} MB", 'white', 'on_blue'))

    
    return output

def log_hardware_info(ssh_client):
    stdin, stdout, stderr = ssh_client.exec_command('cat /proc/cpuinfo')
    output = stdout.read().decode('utf-8')

    lines = []
    found_hardware = False

    for line in output.split('\n'):
        if "Hardware" in line:
            found_hardware = True
        if found_hardware:
            # Strip spaces after colons for all other lines
            line = re.sub(r'\s+', ' ', line).strip()
            line = line.replace(' :', ':')  # Remove space before ":"  
            lines.append(line.strip())
            
    hardware_info = '\n'.join(lines).strip()

    if hardware_info:
        logging.info(colored(hardware_info, 'white', 'on_blue'))
    else:
        logging.info(colored("No hardware information found.", 'white', 'on_red'))

def check_battery():
    print(colored("*** Check Battery installed and PRESS 'y' ***\n", 'white', 'on_blue'))
    check_complete = False

    # Use a while loop to listen for the 'y' key press
    while not check_complete:
        if keyboard.is_pressed('y'):  # Check if 'y' key is pressed
            keyboard.press_and_release('backspace')
            check_complete = True

    # Once 'y' is pressed, continue with the rest of your code
    logging.info(colored("\nBattery check complete.\n", 'white', 'on_green'))
    return 'Battery,'
def check_rtc(ssh_client):
    logging.info(colored("Checking RTC\n", 'white', 'on_blue'))

    logging.info(colored(f"Command executed: timedatectl\n", 'black', 'on_yellow'))

    output = Ssh_Utils.execute_ssh_command(ssh_client, 'timedatectl').strip().split('\n')

    rtc_time_line = next((line for line in output if 'RTC time:' in line), None)

    if rtc_time_line:
        rtc_time = rtc_time_line.split('RTC time:')[1].strip()
        if rtc_time and rtc_time.lower() != 'n/a':
            logging.info(colored(f"RTC time is working: {rtc_time}\n", 'white', 'on_green'))
            return 'RTC,'
    #     else:
    #         logging.info(colored("Failed - RTC time is not working or not available.\n", 'white', 'on_red'))

    # else:
    #     logging.info(colored("Failed - RTC time information not found.\n", 'white', 'on_red'))
    return ''

def check_modpoll(device_path, ssh_client):
    comments = ''
    logging.info(colored(f"Checking Modbus: {device_path}\n", 'white', 'on_blue'))

    shell = ssh_client.invoke_shell()
    thread = threading.Thread(target=run_modpoll, args=(shell, device_path))

    try:
        # Start the thread
        thread.start()
        
        # Allow the command to run for a specific duration (e.g., 10 seconds)
        time.sleep(2)

    finally:
        # Ensure the thread is properly closed
        thread.join()

        # Capture the output
        output = ""
        while shell.recv_ready():
            output += shell.recv(1024).decode('utf-8')

        logging.info(output)

        if "Reply time-out!" in output:
            logging.info(colored("*** Failed - Time-out detected in modpoll output! ***", 'white', 'on_red'))

        elif "Port or socket open error!" in output:
            logging.info(colored("*** Failed - Port error in modpoll output! ***", 'white', 'on_red'))

        elif output.count("[2]") < 3:
            logging.info(colored("*** Failed - Not enough valid replies. ***", 'white', 'on_red'))
        else:
            logging.info(colored(f"Working - No time-out detected in modpoll output.", 'white', 'on_green'))
            comments = f'{device_path[-7:]},'
        
        shell.close()
        logging.info('')

        return comments

def run_modpoll(shell, device_path):
    command = f"modpoll -m rtu -p none -b 9600 -a 1 -t 3:float -r 2 -l 500 -o 2.0 {device_path}\n"

    logging.info(colored(f"Command executed: {command}", 'black', 'on_yellow'))

    shell.send(command)

# add mac address finding to the one below, copy it and make a new one to get the serial number+product_id
def check_eth_interfaces(ssh_client, new_eth1_mac = None):
    comments = ''
    logging.info(colored("Checking ethernet\n", 'white', 'on_blue'))
    logging.info(colored(f"Command executed: ip address\n", 'black', 'on_yellow'))

    output = Ssh_Utils.execute_ssh_command(ssh_client, 'ip address').strip().split('\n')

    eth0_ip = None
    eth1_ip = None
    eth0_mac = None  # Add this line to store MAC address for eth0
    eth1_mac = None  # Add this line to store MAC address for eth1
    current_interface = None
    for line in output:
        if 'eth0:' in line:
            current_interface = 'eth0'
        elif 'eth1:' in line:
            current_interface = 'eth1'
        elif 'inet ' in line and current_interface:
            ip_address = line.split()[1].split('/')[0]
            if ip_address.startswith('192.168.15.'):
                if current_interface == 'eth0':
                    eth0_ip = ip_address
                elif current_interface == 'eth1':
                    eth1_ip = ip_address
            if ip_address.startswith('169.254.'):
                if current_interface == 'eth0':
                    eth0_ip = ip_address
                elif current_interface == 'eth1':
                    eth1_ip = ip_address
        elif 'link/ether' in line and current_interface:  # Check for MAC address line
            mac_address = line.split(" ")[5]
            if current_interface == 'eth0'  and eth1_mac == None:
                eth0_mac = mac_address
            elif current_interface == 'eth1' and eth1_mac == None:
                eth1_mac = mac_address

    if eth0_ip and eth1_ip:
        logging.info(f"eth0 IP Address: {eth0_ip}")
        logging.info(f"eth1 IP Address: {eth1_ip}")
        comments = 'Eth1,Eth2,'
    else:
        logging.info(colored("Failed - eth0 or eth1 does not have a valid IP address.", 'white', 'on_red'))
        logging.info(f"eth0 IP Address: {eth0_ip}")
        logging.info(f"eth1 IP Address: {eth1_ip}")

    if eth0_mac and eth1_mac:
        logging.info(f"eth0 MAC Address: {eth0_mac}")
        logging.info(f"eth1 MAC Address: {eth1_mac}")
        comments += 'MAC1,MAC2,'
    elif eth0_mac == eth1_mac:
        logging.info("Failed - eth0 and eth1 are showing as having the same MAC address.", 'white', 'on_red')
        logging.info(f"eth0 MAC Address: {eth0_mac}")
        logging.info(f"eth1 MAC Address: {eth1_mac}")
    elif new_eth1_mac != eth1_mac:
        logging.info("Failed - eth1 is not the correct MAC address.", 'white', 'on_red')
        logging.info(f"eth0 MAC Address: {eth0_mac}")
        logging.info(f"eth1 MAC Address: {eth1_mac}")
    else:
        logging.info("Failed - eth0 or eth1 does not have a valid MAC address.")
        logging.info(f"eth0 MAC Address: {eth0_mac}")
        logging.info(f"eth1 MAC Address: {eth1_mac}")
    
    logging.info('')
    return comments

def check_rubix_os_folder(ssh_client):
    stdin, stdout, stderr = ssh_client.exec_command('[ -d /data/rubix-os ]')
    exit_status = stdout.channel.recv_exit_status()

    if exit_status == 0:
        return True
    else:
        return False
    
def serial_number(ssh_client):
    stdin, stdout, stderr = ssh_client.exec_command('cat /proc/cpuinfo | grep Serial')
    serial_number = stdout.read().decode('utf-8').split(":")[1].strip()
    return serial_number

def get_all(ssh_client):
    kernel_software_version(ssh_client)
    rc_software_version(ssh_client, True)
    log_hardware_info(ssh_client)
    memory_info = log_memory_info(ssh_client)
    harddrive_info = log_harddrive_info(ssh_client)
    
    logging.info(memory_info)
    logging.info(harddrive_info)
    return

def get_all_C1(ssh_client):
    kernel_software_version(ssh_client)
    logging.info(colored(f"RC software version: 1.0.0", 'white', 'on_blue'))
    log_hardware_info(ssh_client)
    memory_info = log_memory_info(ssh_client)
    harddrive_info = log_harddrive_info(ssh_client)
    
    logging.info(memory_info)
    logging.info(harddrive_info)
    return

def get_file_contents(ssh_client, remote_directory, file_name):
    try:
        # Execute a shell command to read the contents of the file
        command = f"cat {remote_directory}{file_name}"
        contents = ''
        # Get file ifo from local computer
        if(remote_directory == '/home/testbench/product_database/'):
            completed_process = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            contents = completed_process.stdout
        # Get file info from Pi
        else:
            stdin, stdout, stderr = ssh_client.exec_command(command)
            contents = stdout.read().decode('utf-8')
        
        # Split the contents into lines
        lines = contents.split('\n')

        # Initialize variables to store the extracted values
        technician = None
        hardware_version = None
        batch = None
        work_order = None

        # Iterate through the lines and extract the values
        for line in lines:
            if line.startswith("Tester: "):
                technician = line[len("Tester: "):].strip()
            elif line.startswith("Hardware Version: "):
                hardware_version = line[len("Hardware Version: "):].strip()
            elif line.startswith("Batch: "):
                batch = line[len("Batch: "):].strip()
            elif line.startswith("Work Order: "):
                work_order = line[len("Work Order: "):].strip()

        # Return the extracted values
        return technician, hardware_version, batch, work_order
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None, None, None

    

def find_file_by_number(ssh_client, remote_directory, number_of_files):
    try:
        command = f"ls {remote_directory}"
        stdin, stdout, stderr = ssh_client.exec_command(command)
        file_list = stdout.read().decode('utf-8').split()

        pattern = re.compile(r'^.*-#(\d+)\.txt$')

        for file_name in file_list:
            match = pattern.match(file_name)
            if match:
                file_number = int(match.group(1))
                if file_number == number_of_files:
                    return file_name

        # If no matching file is found, return None
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    
def extract_test_data(ssh_client):
    # Used in RC6 tests to see if device was tested already and extract the info
    tested_already = False
    barcode = ''
    hardware_version = ''
    batch_id = ''
    manufacturing_order = ''
    technician = ''

    try:
        output = Ssh_Utils.execute_ssh_command(ssh_client, "python3 /home/rc/scripts/read_eeprom.py")

        # Split the output into lines and extract the relevant values
        lines = output.strip().split('\n')
        data = {}
        for line in lines:
            parts = line.strip().split(': ')
            if len(parts) == 2:
                key, value = parts
                data[key] = value

        # Extract the specific values
        barcode = data.get('Barcode', '')
        hardware_version = data.get('Hardware Version', '')
        batch_id = data.get('Batch', '')
        manufacturing_order = data.get('Manufacturing Order', '')
        technician = data.get('Technician', '')
        test_date = data.get('Date', '')

        if all([barcode, hardware_version, batch_id, manufacturing_order, technician, test_date]):
            tested_already = True

    except Exception as e:
        print(f"An error occurred while extracting test data: {e}")

    return tested_already, barcode, hardware_version, batch_id, manufacturing_order, technician, test_date
