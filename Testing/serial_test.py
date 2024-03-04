import serial
import argparse
import subprocess
import sys
from colorama import *
import time, logging, Custom_Logger
from serial.serialutil import SerialException

logger = Custom_Logger.create_logger('/home/pi/Testing/output.txt')  # Set up the custom logging configuration

# # Check if the logging argument is provided
# if len(sys.argv) > 1:
#     global logger
#     print(sys.argv[1])
#     # Create a logger for this script
#     logger = sys.argv[1]

def get_input():
    response = input(f"{Fore.WHITE}{Back.BLUE}*** Press enter when ready ***\n{Style.RESET_ALL}")


    if response == 'skip':
        return True
    return False



# parser = argparse.ArgumentParser()
# parser.add_argument('-p', metavar='port', type=str,
#                     help='Serial port', default='/dev/ttyACM0')
# parser.add_argument('-b', metavar='baud', type=int,
#                     help='Serial baudrate', default=115200)
# parser.add_argument('-t', metavar='timeout', type=int,
#                     help='Serial timeout', default=0.25)
# parser.add_argument('-v', metavar='version', type=str,
#                     help='Firmware vesion', default='4.0.0')
# parser.add_argument('--prod', action='store_true',
#                     help='Speeds up tests for prod builds', default=True)
# parser.add_argument('--bin-file', metavar='filename', type=str,
#                     help='Binary firmware file', default='bin/R-IO-16-Modbus_v4.0.0_F411RE.bin')



port = '/dev/ttyACM0'
baud = 115200
timeout = 0.25
prod = True
version_fw = '4.0.0'


OK = b'OK'
ERROR = b'ERROR'
UNKNOWN = b'UNKNOWN'


def send(cmdFull, resp=OK):
    type = b''
    if b'?' in cmdFull:
        type = b'?'
    elif b'=' in cmdFull:
        type = b'='

    cmd = cmdFull
    if type != b'':
        cmd = cmdFull[:cmdFull.index(type)]
    logger.info('CMD: %s', cmdFull)

    while ser.in_waiting:
        ser.readline()

    ser.write(b'AT+')
    ser.write(cmdFull)
    ser.write(b'\n')

    line = None
    while not line or line[0] == b'\0' or line[0] == b'['[0]:
        line = ser.readline()

    assert(line != b'')

    ans = line[:line.index(b'\n')]

    if resp != UNKNOWN and type == b'?':
        assert(ans.index(b'+') == 0)
        assert(ans.index(b':') == len(cmd) + 1)
        assert(ans[1:ans.index(b':')] == cmd)
        ans = ans[ans.index(b':') + 1:]
    logger.info('ANS: %s', ans)
    return ans


def check(cmdFull, resp=OK):
    ans = send(cmdFull, resp)
    try:
        if isinstance(resp, list) and isinstance(resp[0], bytes):
            assert(ans in resp)
        if isinstance(resp, list) and isinstance(resp[0], int):
            assert(len(ans) >= resp[0] and len(ans) <= resp[1])
        elif isinstance(resp, int):
            assert(len(ans) == resp)
        elif isinstance(resp, str):
            assert(ans == bytes(resp, 'utf-8'))
        elif isinstance(resp, bytes):
            assert(ans == resp)
    except AssertionError as e:
        logger.info(f"{Fore.WHITE}{Back.RED}\u2717 FAILED{Style.RESET_ALL}")
        logger.info('Assertion Error')
        
        return False

    if prod:
        time.sleep(0.02)
    else:
        time.sleep(0.08)

    logger.info(f"{Fore.BLACK}{Back.GREEN}\u2713 PASSED{Style.RESET_ALL}")

    return True

def clearSettStd():
    check(b'CLEARSETTINGSSTD', OK)
    if prod:
        time.sleep(0.25)
    else:
        time.sleep(0.7)


def clearSettRbx():
    check(b'CLEARSETTINGSRBX', OK)
    if prod:
        time.sleep(0.25)
    else:
        time.sleep(0.7)

def get_serial_port():
    # For USB serial, we need to re-open the serial port after a device reset
    ser.close()
    time.sleep(0.2)
    while True:
        try:
            ser.open()
        except SerialException:
            # try the port number above or below since the reset happens
            #  too fast for PCs to reassign the device to the same port
            serNum = int(ser.port[-1])
            if ser.port == port:
                serNum += 1
            else:
                serNum -= 1
            ser.port = ser.port[:-1] + str(serNum)
            continue
        break

def reset():
    check(b'SOFTRESET', OK)
    logger.info('sleeping for 2\n')
    if prod:
        time.sleep(1.2)
    else:
        time.sleep(2)
    line = None

    get_serial_port()
    ser.readline()
    while ser.in_waiting or line != b'':
        line = ser.readline()
        #  logger.info(line)

def version():
    global version_fw
    logger.info(f"{Fore.BLACK}{Back.YELLOW}Checking Version{Style.RESET_ALL}")
    installed_version = send(b'VERSION?').decode('utf-8')

    if not version_fw == installed_version:
        logger.info(f"{Fore.WHITE}{Back.RED}\u2717 Incorrect version detected{Style.RESET_ALL}")
        exit()
    else:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}" f"Firmware: {installed_version}" f"{Style.RESET_ALL}")


def modbAddr():
    logger.info(f"{Fore.BLACK}{Back.YELLOW}Checking Modbus address{Style.RESET_ALL}")

    passed = False
    while not passed:
        passed = check(b'MODBADDR?', b'1')
        if not passed:
            logger.info(colored('Set dips to 00000001 00000001', 'black', 'on_yellow'))
            if get_input():
                break
            reset()




def dipswitches():
    logger.info(f"{Fore.BLACK}{Back.YELLOW}Checking dip switches{Style.RESET_ALL}")

    passed = False
    ATS = 0
    while not passed and ATS < 3:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Set dips to 01000011 01000011{Style.RESET_ALL}")

        if get_input():
            break
        reset()
        passed = check(b'DIPSWITCHES?', b'00000010 01000000')
        ATS = ATS+1

    logger.info(f"{Fore.BLACK}{Back.GREEN}\u2713 PASSED{Style.RESET_ALL}")

    if ATS < 3:
        ATS = 0
        passed = False
        while not passed and ATS < 3:
            logger.info(f"{Fore.BLACK}{Back.YELLOW}Set dips to 00000001 00000001{Style.RESET_ALL}")

            if get_input():
                break
            reset()
            passed = check(b'DIPSWITCHES?', b'00000000 00000000')
            ATS = ATS + 1


    if ATS >= 3:
        logger.info("Mark for ATS use only")
        input(f"{Fore.WHITE}{Back.BLUE}*** Press enter once marked ***{Style.RESET_ALL}")

def loradetect():
    logger.info(f"{Fore.BLACK}{Back.YELLOW}Checking LoRa chip{Style.RESET_ALL}")

    passed = False
    while not passed:
        passed = check(b'LORADETECT?', b'1')
        if not passed:
            logger.info(f"{Fore.WHITE}{Back.RED}\u2717 LoRa not detected{Style.RESET_ALL}")
            logger.info(f"{Fore.BLACK}{Back.YELLOW}Plug in LoRa module and try again{Style.RESET_ALL}")
            if get_input():
                break




class bcolors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def test(func):
    logger.info(f'->{bcolors.BOLD} {func.__name__}{bcolors.ENDC}')
    func()
    logger.info(f"{Fore.BLACK}{Back.GREEN}\u2713 PASSED{Style.RESET_ALL}")


def dipswitches_all():
    logger.info(f"{Fore.BLACK}{Back.YELLOW}Checking dip switches{Style.RESET_ALL}")

    passed = False
    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Set dips to 10000001 10000001{Style.RESET_ALL}")

        if get_input():
            break
        reset()
        passed = check(b'DIPSWITCHES?', b'10000000 10000000')


    passed = False
    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Set dips to 01000001 01000001{Style.RESET_ALL}")

        if get_input():
            break
        reset()
        passed = check(b'DIPSWITCHES?', b'01000000 01000000')


    passed = False
    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Set dips to 00100001 00100001{Style.RESET_ALL}")

        if get_input():
            break
        reset()
        passed = check(b'DIPSWITCHES?', b'00100000 00100000')

    passed = False
    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Set dips to 10100001 10100001{Style.RESET_ALL}")

        if get_input():
            break
        reset()
        passed = check(b'DIPSWITCHES?', b'10100000 10100000')

    passed = False
    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Set dips to 00010001 00000001{Style.RESET_ALL}")

        if get_input():
            break
        reset()
        passed = check(b'DIPSWITCHES?', b'00010000 00000000')

    passed = False
    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Set dips to 00000001 00000001{Style.RESET_ALL}")

        if get_input():
            break
        reset()
        passed = check(b'DIPSWITCHES?', b'00000000 00000000')

start_time = time.time()

with serial.Serial(port, baud, timeout=timeout) as ser:
    # flash_device()
    get_serial_port()
    ser.readline()
    while ser.in_waiting:
        ser.readline()
    
    logger.info(f'Unique_ID: {send(b"LRRADDRUNQ?").decode("utf-8")}')

    test(version)
    #test(dipswitches)
    test(dipswitches_all)
    test(modbAddr)
    test(loradetect)


logger.info(f'Tests completed in: {round(time.time()-start_time, 2)}s')
