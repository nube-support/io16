# ssh_utils.py
import subprocess, os, logging, paramiko, time, socket
from termcolor import colored

def is_rpi_reachable(hostname, timeout=1, count=1):
    response = subprocess.run(['ping', '-c', str(count), '-W', str(timeout), hostname], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return response.returncode == 0

def connect_to_rpi(hostname, username, password, port=None):
    # try:
    #     s = socket.socket()
    #     s.bind(('192.168.15.98', 0))
    #     s.connect((hostname, 2022))
    # except Exception as e:
    #     print(f"An error occurred: [SSH_Utils] Socket binding error. {e}. Check ethernet cable connections to device.")
    #     exit(1)
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    while True:
        try:
            if port is not None:
                ssh_client.connect(hostname=hostname, username=username, password=password, port=port)
                #ssh_client.connect(hostname=hostname, username=username, password=password, sock=s)

            else:
                ssh_client.connect(hostname=hostname, username=username, key_filename='/home/testbench/.ssh/id_rsa')
                #ssh_client.connect(hostname=hostname, username=username, password=password, sock=s)

            return ssh_client
        except paramiko.ssh_exception.NoValidConnectionsError:
            print("Unable to connect. Retrying in 1 second...")
            time.sleep(1)  # Wait for 1 seconds before retrying
        except Exception as e:
            print(f"An error occurred: {e}")
            break

def close_connection(ssh_client):
    ssh_client.close()

def execute_ssh_command(ssh_client, command):
    stdin, stdout, stderr = ssh_client.exec_command(command)

    return stdout.read().decode('utf-8')

def transfer_file(ssh_client, local_path, remote_path):
    sftp = ssh_client.open_sftp()
    sftp.put(local_path, remote_path)
    sftp.close()

def print_barcodes():
    try:
        # Print the barcode for the board
        cmd = "lpr -P PT-P900W -o PageSize=Custom.12x32mm -o Resolution=360dpi -o CutLabel=0 -o ExtraMargin=0mm -o number-up=1 -o orientation-requested=4 /home/testbench/rubix-compute-man/images/barcode.png"
        subprocess.check_output(cmd, shell=True, text=True)

        # Prepare and print the stickers for the enclosure

        cmd = "lpr -P PT-P900W -o PageSize=Custom.12x50mm -o Resolution=360dpi -o CutLabel=0 -o ExtraMargin=0mm -o number-up=1 -o orientation-requested=4 -#2 /home/testbench/rubix-compute-man/images/product_label.png"
        subprocess.check_output(cmd, shell=True, text=True)
    except Exception as e:
        print(f"An error occurred: {e}")
        return

def test_lora(ssh_client, remote_directory):
    # Get the parent directory
    remote_root = os.path.dirname(os.path.normpath(remote_directory))

    sftp = ssh_client.open_sftp()
    # Test LoRa
    try:
        sftp.chdir(remote_directory)  # Attempt to change to the directory

        sftp.put('helpers/testing_scripts_for_ssh/nubeio-rubix-app-lora-serial-py', f"{remote_directory}/nubeio-rubix-app-lora-serial-py")

        # Close the SFTP connection
        sftp.close()
    except IOError:
        sftp.mkdir(remote_directory)  # Create the directory if it doesn't exist
        sftp.chdir(remote_directory)  # Change to the new directory

        # Transfer LoRa testing script
        a = sftp.put('helpers/testing_scripts_for_ssh/nubeio-rubix-app-lora-serial-py', f"{remote_directory}/nubeio-rubix-app-lora-serial-py")

        # Close the SFTP connection
        sftp.close()

    # Test LoRa connection
    output = execute_ssh_command(ssh_client, f"sudo chmod +x {remote_directory}/nubeio-rubix-app-lora-serial-py")

    output = execute_ssh_command(ssh_client, f"sudo ./testing/nubeio-rubix-app-lora-serial-py > output.txt 2>&1 &")

    print(colored("Testing LoRa connection, this can take a few seconds...\n", 'white', 'on_blue'))

    time.sleep(2)
    #sending_device_serial = AT_Commands_ME.command(b'LRRADDRUNQ?').lower()

    push = AT_Commands_ME.command(b'LORARAWPUSH')
    print(f"LoRa package sent, status: {push}")
    
    time.sleep(5)

    sftp = ssh_client.open_sftp()

    attempts = 1
    while attempts <= 8:

        # Get LoRa test file info from device
        sftp.get(f"{remote_root}/output.txt", "loRa_output.txt")


        # Read the content of the file to check for the test signal sent from our sending device ()
        with open("loRa_output.txt", "r") as file:
            file_content = file.read()

        sending_device_serial = 'aaacaaaa'
        signal_received = sending_device_serial in file_content
        if signal_received:
            break
        push = AT_Commands_ME.command(b'LORARAWPUSH')
        print(f"LoRa package sent, status: {push}")
        
        time.sleep(2)
        attempts += 1

    sftp.close()

    if signal_received:
        logging.info(colored(f"LoRa signal received from test device with {sending_device_serial.upper()} serial number, module working.", 'white', 'on_green'))
    else:
        logging.info(colored(f"Failed - LoRa signal not received from test device with {sending_device_serial.upper()} serial number.", 'white', 'on_red'))

    # Remove the LoRa testing files from the Pi as a clean up
    execute_ssh_command(ssh_client, f"rm {remote_directory}nubeio-rubix-app-lora-serial-py")
    execute_ssh_command(ssh_client, f"rm {remote_root}/output.txt")

    return signal_received
# Add more SSH-related functions as needed

def copy_files_to_directory(ssh_client, remote_directory, files_to_copy):
    sftp = ssh_client.open_sftp()
    
    try:
        sftp.chdir(remote_directory)  # Attempt to change to the directory
    except IOError:
        sftp.mkdir(remote_directory)  # Create the directory if it doesn't exist
        sftp.chdir(remote_directory)  # Change to the new directory

    for file_path in files_to_copy:
        local_file = os.path.join(file_path)
        remote_file = os.path.join(remote_directory, os.path.basename(file_path))

        # Transfer the file
        sftp.put(local_file, remote_file)

    # Close the SFTP connection
    sftp.close()

