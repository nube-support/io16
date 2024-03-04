from termcolor import *
import serial
import argparse
import subprocess
import sys
import time
from serial.serialutil import SerialException

def get_input():
    response = input(colored("*** Press enter when ready ***", 'white', 'on_blue'))
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
version = '4.0.0'


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
    print('CMD: ', cmdFull)

    while ser.in_waiting:
        ser.readline()
        #  print(ser.readline())

    ser.write(b'AT+')
    ser.write(cmdFull)
    ser.write(b'\n')

    line = None
    while not line or line[0] == b'\0' or line[0] == b'['[0]:
        line = ser.readline()
        #  print(line)

    assert(line != b'')

    ans = line[:line.index(b'\n')]
    if resp != UNKNOWN and type == b'?':
        assert(ans.index(b'+') == 0)
        assert(ans.index(b':') == len(cmd) + 1)
        assert(ans[1:ans.index(b':')] == cmd)
        ans = ans[ans.index(b':') + 1:]
    print('ANS: ', ans)
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
        print(colored('\u2717 FAILED', 'white', 'on_red'))
        print(e)
        return False

    if prod:
        time.sleep(0.02)
    else:
        time.sleep(0.08)

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
    print('sleeping for 2\n')
    if prod:
        time.sleep(0.75)
    else:
        time.sleep(0.75)
    line = None

    get_serial_port()
    ser.readline()
    while ser.in_waiting or line != b'':
        line = ser.readline()
        #  print(line)

def version():
    print(colored('Checking Version', 'black', 'on_yellow'))
    if not check(b'VERSION?', version):
        print(colored('\u2717 Incorrect version detected', 'white', 'on_red'))
        exit()


def modbAddr():
    print(colored('Checking Modbus address', 'black', 'on_yellow'))
    passed = False
    while not passed:
        passed = check(b'MODBADDR?', b'1')
        if not passed:
            print(colored('Set dips to 00000001 00000001', 'black', 'on_yellow'))
            if get_input():
                break
            reset()




def dipswitches():
    print(colored('Checking dip switches', 'black', 'on_yellow'))
    passed = False
    ATS = 0
    while not passed and ATS < 3:
        print(colored('Set dips to 01000011 01000011', 'black', 'on_yellow'))
        if get_input():
            break
        reset()
        passed = check(b'DIPSWITCHES?', b'01000010 01000010')
        ATS = ATS+1

    print(colored('\u2713 PASSED', 'black', 'on_green'))
    if ATS < 3:
        ATS = 0
        passed = False
        while not passed and ATS < 3:
            print(colored('Set dips to 00000001 00000001', 'black', 'on_yellow'))
            if get_input():
                break
            reset()
            passed = check(b'DIPSWITCHES?', b'00000000 00000000')
            ATS = ATS + 1


    if ATS >= 3:
        print("Mark for ATS use only")
        input(colored("*** Press enter once marked ***", 'white', 'on_blue'))

def loradetect():
    print(colored('Checking LoRa chip', 'black', 'on_yellow'))
    passed = False
    while not passed:
        passed = check(b'LORADETECT?', b'1')
        if not passed:
            print(colored('\u2717 LoRa not detected', 'white', 'on_red'))
            print(colored('Plug in LoRa module and try again', 'black', 'on_yellow'))
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
    print(f'->{bcolors.BOLD} {func.__name__}{bcolors.ENDC}')
    func()
    print(colored('\u2713 PASSED', 'black', 'on_green'))



def dipswitches_all():
    print(colored('Checking dip switches', 'black', 'on_yellow'))
    passed = False
    while not passed:
        print(colored('Set dips to 00000001 00000001', 'black', 'on_yellow'))
        if get_input():
            break
        reset()
        passed = check(b'DIPSWITCHES?', b'00000000 00000000')

    passed = False
    while not passed:
        print(colored('Set dips to 10000001 00000001', 'black', 'on_yellow'))
        if get_input():
            break
        reset()
        passed = check(b'DIPSWITCHES?', b'10000000 00000000')


    passed = False
    while not passed:
        print(colored('Set dips to 01000001 00000001', 'black', 'on_yellow'))
        if get_input():
            break
        reset()
        passed = check(b'DIPSWITCHES?', b'01000000 00000000')

    passed = False
    while not passed:
        print(colored('Set dips to 11000001 00000001', 'black', 'on_yellow'))
        if get_input():
            break
        reset()
        passed = check(b'DIPSWITCHES?', b'11000000 00000000')

    passed = False
    while not passed:
        print(colored('Set dips to 00100001 00000001', 'black', 'on_yellow'))
        if get_input():
            break
        reset()
        passed = check(b'DIPSWITCHES?', b'00100000 00000000')

    passed = False
    while not passed:
        print(colored('Set dips to 10100001 00000001', 'black', 'on_yellow'))
        if get_input():
            break
        reset()
        passed = check(b'DIPSWITCHES?', b'10100000 00000000')

    passed = False
    while not passed:
        print(colored('Set dips to 11100001 00000001', 'black', 'on_yellow'))
        if get_input():
            break
        reset()
        passed = check(b'DIPSWITCHES?', b'11100000 00000000')

    passed = False
    while not passed:
        print(colored('Set dips to 00010001 00000001', 'black', 'on_yellow'))
        if get_input():
            break
        reset()
        passed = check(b'DIPSWITCHES?', b'00010000 00000000')



start_time = time.time()

with serial.Serial(port, baud, timeout=timeout) as ser:
    # flash_device()
    get_serial_port()
    ser.readline()
    while ser.in_waiting:
        ser.readline()

    test(dipswitches_all)



print(f'Tests completed in: {round(time.time()-start_time, 2)}s')