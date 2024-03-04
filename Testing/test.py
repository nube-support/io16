import argparse
import subprocess
import sys
import time, logging, paramiko, pysftp
from colorama import *
import numpy as np
from modbus_commands import *
import Custom_Logger
# from serial_test import *

parser = argparse.ArgumentParser()
parser.add_argument('--port-modb', metavar='port', type=str,
                    help='Modbus Serial port', default='/dev/ttyUSB0')
parser.add_argument('--port-usb', metavar='port', type=str,
                    help='USB Serial port', default='/dev/ttyACM0')
parser.add_argument('--bin-file', metavar='filename', type=str,
                    help='Binary firmware file', default='R-IO-16-Modbus_v4.0.0_F411RE.bin')
parser.add_argument('--pre23', action='store_true', help='Set this flag if hardware is pre 2023')
args = parser.parse_args()

UO_COUNT = 8
UI_COUNT = 8
DO_COUNT = 0

UO_0_10_ACCEPTED_ERROR = 1
EPSILON = 0.000001

logger = Custom_Logger.create_logger('/home/pi/Testing/output.txt')  # Set up the custom logging configuration

def get_input():
    response = input(f"{Fore.WHITE}{Back.BLUE}*** Press enter when ready ***\n{Style.RESET_ALL}")
    if response == 'skip':
        return True
    return False

def check_Correct(expected_result, result, range_value):
    try:
        difference = np.abs(expected_result - result)
        assert np.all(difference <= range_value)

        # Check if the result is a list and stringify it
        if isinstance(result, list):
            result = str(result)

        # Check if the expected_result is a list and stringify it
        if isinstance(expected_result, list):
            expected_result = str(expected_result)

        logger.info(expected_result)
        logger.info(result)
        logger.info(f"{Fore.WHITE}{Back.GREEN}\u2713 Passed{Style.RESET_ALL}")

        return True
    except AssertionError as e:
        logger.info(f"{Fore.WHITE}{Back.RED}\u2717 Failed:{Style.RESET_ALL}")

        logger.info('Expected result:')
        logger.info(expected_result)
        logger.info("Result:")
        logger.info(result)
        logger.info(f"{Fore.BLACK}{Back.YELLOW}\u2717 Try Again{Style.RESET_ALL}")
        logger.info('')
        return False


def reset_ui_calabration():
    logger.info(f"{Fore.BLACK}{Back.YELLOW}\u2717 Resetting UI calibration{Style.RESET_ALL}")

    passed = False

    default_coeff = np.array([1] * 8)
    default_offset = np.array([0] * 8)
    write_all_ui_calib_coeff(default_coeff)
    write_all_ui_calib_offset(default_offset)
    passed = check_Correct(default_coeff, np.array(read_ui_calib_coeff()), 0)
    passed = check_Correct(default_offset, np.array(read_ui_calib_offset()), 0) and passed
    if not passed:
        logger.info(f"{Fore.WHITE}{Back.RED}Failed to reset UI calibration:{Style.RESET_ALL}")
        exit()


def reset_uo_calabration():
    logger.info(f"{Fore.BLACK}{Back.YELLOW}Resetting UO calibration{Style.RESET_ALL}")

    passed = False

    default_coeff = np.array([1] * 8)
    default_offset = np.array([0] * 8)
    write_all_UO_calib_coeff(default_coeff)
    write_all_UO_calib_offset(default_offset)
    passed = check_Correct(default_coeff, np.array(read_uo_calib_coeff()), 0)
    passed = check_Correct(default_offset, np.array(read_uo_calib_offset()), 0) and passed
    if not passed:
        logger.info(f"{Fore.WHITE}{Back.RED}Failed to reset UO calibration:{Style.RESET_ALL}")
        exit()


def calabrate_0_10V():
    expected_result_7_5 = np.array([750] * 8)
    expected_result_5_0 = np.array([500] * 8)
    expected_result_2_5 = np.array([250] * 8)

    # voltageIn7_5 = np.array([747, 747, 748, 749, 748, 749, 749, 747])
    # voltageIn5_0 = np.array([496, 497, 498, 499, 498, 499, 498, 497])
    # voltageIn2_5 = np.array([246, 247, 248, 248, 248, 248, 248, 247])
    voltageIn7_5 = np.array([])
    voltageIn5_0 = np.array([])
    voltageIn2_5 = np.array([])

    logger.info(f"{Fore.BLACK}{Back.YELLOW}Testing 0-10V inputs, Check inputs set to 0-10V{Style.RESET_ALL}")

    passed = False
    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Connect inputs to 7.5V{Style.RESET_ALL}")

        if get_input():
            break
        voltageIn7_5 = np.array(read_ui_0_10_all())
        passed = check_Correct(expected_result_7_5, voltageIn7_5, 20)

    
    passed = False

    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Connect inputs to 5V{Style.RESET_ALL}")

        if get_input():
            break
        voltageIn5_0 = np.array(read_ui_0_10_all())
        passed = check_Correct(expected_result_5_0, voltageIn5_0, 20)

    
    passed = False

    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Connect inputs to 2.5V{Style.RESET_ALL}")

        if get_input():
            break
        voltageIn2_5 = np.array(read_ui_0_10_all())
        passed = check_Correct(expected_result_2_5, voltageIn2_5, 20)

    logger.info(f"{Fore.BLACK}{Back.YELLOW}Calibrating UI{Style.RESET_ALL}")

    m = (expected_result_7_5 - expected_result_2_5 + voltageIn2_5) / voltageIn7_5
    o_2_5 = (expected_result_2_5 - voltageIn2_5 * m)
    o_5_0 = (expected_result_5_0 - voltageIn5_0 * m)
    o_7_5 = (expected_result_7_5 - voltageIn7_5 * m)
    matrix_stack = np.stack((o_2_5, o_5_0, o_7_5))
    o = np.mean(matrix_stack, axis=0) / 100
    logger.info(m)
    logger.info(o)

    
    passed = False
    logger.info(f"{Fore.BLACK}{Back.YELLOW}Checking UI calibration{Style.RESET_ALL}")

    passed = check_Correct(expected_result_2_5, voltageIn2_5 * m + o * 100, 2)
    passed = check_Correct(expected_result_5_0, voltageIn5_0 * m + o * 100, 2) and passed
    passed = check_Correct(expected_result_7_5, voltageIn7_5 * m + o * 100, 2) and passed

    if not passed:
        logger.info(f"{Fore.WHITE}{Back.RED}UI calibration failed, not within range{Style.RESET_ALL}")

        exit()

    logger.info(f"{Fore.BLACK}{Back.YELLOW}Writing UI Calibrations{Style.RESET_ALL}")

    passed = False
    write_all_ui_calib_coeff(m)
    write_all_ui_calib_offset(o)
    passed = check_Correct(m, np.array(read_ui_calib_coeff()), 0.0001)
    passed = check_Correct(o, np.array(read_ui_calib_offset()), 0.0001) and passed

    if not passed:
        logger.info(f"{Fore.WHITE}{Back.RED}Failed to write UI calibration:{Style.RESET_ALL}")
        exit()


def calabrate_UI_raw():
    expected_result_7_5 = np.array([0.75] * 8)
    expected_result_5_0 = np.array([0.5] * 8)
    expected_result_2_5 = np.array([0.25] * 8)

    # voltageIn7_5 = np.array([747, 747, 748, 749, 748, 749, 749, 747])
    # voltageIn5_0 = np.array([496, 497, 498, 499, 498, 499, 498, 497])
    # voltageIn2_5 = np.array([246, 247, 248, 248, 248, 248, 248, 247])
    voltageIn7_5 = np.array([0.75] * 8)
    voltageIn5_0 = np.array([0.5] * 8)
    voltageIn2_5 = np.array([0.25] * 8)

    logger.info(f"{Fore.BLACK}{Back.YELLOW}Testing 0-10V inputs, Check inputs set to 0-10V{Style.RESET_ALL}")

    passed = False
    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Connect inputs to 7.5V{Style.RESET_ALL}")

        if get_input():
            break
        voltageIn7_5 = np.array(read_ui_raw_all())
        passed = check_Correct(expected_result_7_5, voltageIn7_5, 0.02)

    
    passed = False
    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Connect inputs to 5V{Style.RESET_ALL}")

        if get_input():
            break
        voltageIn5_0 = np.array(read_ui_raw_all())
        passed = check_Correct(expected_result_5_0, voltageIn5_0, 0.02)

    
    passed = False
    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Connect inputs to 2.5V{Style.RESET_ALL}")

        if get_input():
            break
        voltageIn2_5 = np.array(read_ui_raw_all())
        passed = check_Correct(expected_result_2_5, voltageIn2_5, 0.02)

    logger.info(f"{Fore.BLACK}{Back.YELLOW}Calibrating UI{Style.RESET_ALL}")

    m = (expected_result_7_5 - expected_result_2_5 + voltageIn2_5) / voltageIn7_5
    o_2_5 = (expected_result_2_5 - voltageIn2_5 * m)
    o_5_0 = (expected_result_5_0 - voltageIn5_0 * m)
    o_7_5 = (expected_result_7_5 - voltageIn7_5 * m)
    matrix_stack = np.stack((o_2_5, o_5_0, o_7_5))
    o = np.mean(matrix_stack, axis=0)
    logger.info(m)
    logger.info(o)

    
    passed = False
    logger.info(f"{Fore.BLACK}{Back.YELLOW}Checking UI calibration{Style.RESET_ALL}")

    passed = check_Correct(expected_result_2_5, voltageIn2_5 * m + o, 0.01)
    passed = check_Correct(expected_result_5_0, voltageIn5_0 * m + o, 0.01) and passed
    passed = check_Correct(expected_result_7_5, voltageIn7_5 * m + o, 0.01) and passed

    if not passed:
        logger.info(f"{Fore.WHITE}{Back.RED}UI calibration failed, not within range{Style.RESET_ALL}")

        exit()
    #
    logger.info(f"{Fore.BLACK}{Back.YELLOW}Writing UI Calibrations{Style.RESET_ALL}")
 
    passed = False
    write_all_ui_calib_coeff(m)
    write_all_ui_calib_offset(o)
    passed = check_Correct(m, np.array(read_ui_calib_coeff()), 0.0001)
    passed = check_Correct(o, np.array(read_ui_calib_offset()), 0.0001) and passed

    if not passed:
        logger.info(f"{Fore.WHITE}{Back.RED}Failed to write UI calibration:{Style.RESET_ALL}")

        exit()

    logger.info(f"{Fore.BLACK}{Back.GREEN}\u2713 UI calibration complete{Style.RESET_ALL}")

def calabrate_UO_0_10V():
    expected_result_7_5 = np.array([750] * 8)
    expected_result_5_0 = np.array([500] * 8)
    expected_result_2_5 = np.array([250] * 8)

    voltageIn7_5 = np.array([750] * 8)
    voltageIn5_0 = np.array([500] * 8)
    voltageIn2_5 = np.array([250] * 8)

    logger.info(f"{Fore.BLACK}{Back.YELLOW}Testing 0-10V Outputs, Check inputs and outputs are set to 0-10V{Style.RESET_ALL}")

    passed = False
    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Connect outputs to inputs{Style.RESET_ALL}")

        if get_input():
            break
        write_uo_0_10_all(expected_result_7_5)
        time.sleep(0.4)
        # logger.info(read_uo_raw())
        voltageIn7_5 = np.array(read_ui_0_10_all())
        passed = check_Correct(expected_result_7_5, voltageIn7_5, 50)
        if not passed:
            continue

        time.sleep(0.4)
        write_uo_0_10_all(expected_result_5_0)
        time.sleep(0.4)
        # logger.info(read_uo_raw())
        voltageIn5_0 = np.array(read_ui_0_10_all())
        passed = check_Correct(expected_result_5_0, voltageIn5_0, 50)
        if not passed:
            continue

        time.sleep(0.4)
        write_uo_0_10_all(expected_result_2_5)
        time.sleep(0.4)
        # logger.info(read_uo_raw())
        voltageIn2_5 = np.array(read_ui_0_10_all())
        passed = check_Correct(expected_result_2_5, voltageIn2_5, 50)
        if not passed:
            continue

        logger.info(f"{Fore.BLACK}{Back.YELLOW}Calibrating UO{Style.RESET_ALL}")

        m = (expected_result_7_5 - expected_result_2_5 + voltageIn2_5) / voltageIn7_5
        o_2_5 = (expected_result_2_5 - voltageIn2_5 * m)
        o_5_0 = (expected_result_5_0 - voltageIn5_0 * m)
        o_7_5 = (expected_result_7_5 - voltageIn7_5 * m)
        matrix_stack = np.stack((o_2_5, o_5_0, o_7_5))
        o = np.mean(matrix_stack, axis=0)
        #
        # m_2_5 = (expected_result_2_5/voltageIn2_5)
        # m_5_0 = (expected_result_5_0/voltageIn5_0)
        # m_7_5 = (expected_result_7_5/voltageIn7_5)
        # matrix_stack_m = np.stack((m_2_5, m_5_0, m_7_5))
        # m = np.mean(matrix_stack_m, axis=0)
        # o = np.array([0] * 8)
        logger.info(m)
        logger.info(o)

        passed = False
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Checking UI calibration{Style.RESET_ALL}")

        passed = check_Correct(expected_result_2_5, voltageIn2_5 * m + o, 10)
        passed = check_Correct(expected_result_5_0, voltageIn5_0 * m + o, 10) and passed
        passed = check_Correct(expected_result_7_5, voltageIn7_5 * m + o, 10) and passed

        if not passed:
            logger.info(f"{Fore.WHITE}{Back.RED}UO calibration failed, not within range{Style.RESET_ALL}")
            logger.info('')
            continue

        logger.info(f"{Fore.BLACK}{Back.YELLOW}UO calibration failed, not within range{Style.RESET_ALL}")

        passed = False
        write_all_UO_calib_coeff(m)
        write_all_UO_calib_offset(o/100)
        passed = check_Correct(m, np.array(read_uo_calib_coeff()), 0.0001)
        passed = check_Correct(o/100, np.array(read_uo_calib_offset()), 0.0001) and passed

        if not passed:
            logger.info(f"{Fore.WHITE}{Back.RED}UO calibration failed, not within range{Style.RESET_ALL}")
            time.sleep(0.1)
            exit()

            logger.info(f"{Fore.BLACK}{Back.GREEN}\u2713 UO calibration complete{Style.RESET_ALL}")

def check_voltage_in_out():
    expected_result_10_0 = np.array([1000] * 8)
    expected_result_7_5 = np.array([750] * 8)
    expected_result_5_0 = np.array([500] * 8)
    expected_result_2_5 = np.array([250] * 8)
    expected_result_0_0 = np.array([0] * 8)

    voltageIn7_5 = np.array([])
    voltageIn5_0 = np.array([])
    voltageIn2_5 = np.array([])

    logger.info(f"{Fore.BLACK}{Back.YELLOW}Checking 0-10V Inputs/Outputs, Check inputs and outputs are set to 0-10V{Style.RESET_ALL}")

    passed = False
    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Connect outputs to inputs{Style.RESET_ALL}")

        if get_input():
            break
        write_uo_0_10_all(expected_result_7_5)
        time.sleep(0.2)
        logger.info(str(read_uo_raw()))
        voltageIn7_5 = np.array(read_ui_0_10_all())
        passed = check_Correct(expected_result_7_5, voltageIn7_5, 20)
        if not passed:
            continue

        time.sleep(0.2)
        write_uo_0_10_all(expected_result_5_0)
        time.sleep(0.2)
        logger.info(str(read_uo_raw()))
        voltageIn5_0 = np.array(read_ui_0_10_all())
        passed = check_Correct(expected_result_5_0, voltageIn5_0, 20)
        if not passed:
            continue

        time.sleep(0.2)
        write_uo_0_10_all(expected_result_2_5)
        time.sleep(0.2)
        logger.info(str(read_uo_raw()))
        voltageIn2_5 = np.array(read_ui_0_10_all())
        passed = check_Correct(expected_result_2_5, voltageIn2_5, 20)
        if not passed:
            continue


        time.sleep(0.2)
        write_uo_0_10_all(expected_result_10_0)
        time.sleep(0.2)
        logger.info(str(read_uo_raw()))
        voltageIn = np.array(read_ui_0_10_all())
        passed = check_Correct(expected_result_10_0, voltageIn, 20)
        if not passed:
            continue

        time.sleep(0.2)
        logger.info(expected_result_0_0)
        write_uo_0_10_all(expected_result_0_0)
        time.sleep(0.2)
        logger.info(str(read_uo_raw()))
        voltageIn = np.array(read_ui_0_10_all())
        passed = check_Correct(expected_result_0_0, voltageIn, 10)
        if not passed:
            continue

        logger.info(f"{Fore.BLACK}{Back.GREEN}\u2713 UIO voltage check complete{Style.RESET_ALL}")



def check_10k_resistance():
    error_multipler = 1
    if args.pre23:
        error_multipler = 3
    expected_result_5k = np.array([5000] * 8)
    expected_result_10k = np.array([10000] * 8)
    expected_result_37k = np.array([37300] * 8)

    resistanceIn5k = np.array([])
    resistanceIn10k = np.array([])
    resistanceIn37k = np.array([])

    logger.info(f"{Fore.BLACK}{Back.YELLOW}Testing Resistance inputs, Check inputs set to 10K{Style.RESET_ALL}")

    passed = False
    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Connect inputs to 5K{Style.RESET_ALL}")

        if get_input():
            break
        logger.info(str(read_ui_10k_all()))
        resistanceIn5k = np.array(read_ui_10k_resistance())
        passed = check_Correct(expected_result_5k, resistanceIn5k, 75*error_multipler)



    passed = False
    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Connect inputs to 10K{Style.RESET_ALL}")

        if get_input():
            break
        logger.info(str(read_ui_10k_all()))
        resistanceIn10k = np.array(read_ui_10k_resistance())
        passed = check_Correct(expected_result_10k, resistanceIn10k, 150*error_multipler)

    
    passed = False
    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Connect inputs to 37.3K{Style.RESET_ALL}")

        if get_input():
            break
        logger.info(str(read_ui_10k_all()))
        resistanceIn37k = np.array(read_ui_10k_resistance())
        passed = check_Correct(expected_result_37k, resistanceIn37k, 1000*error_multipler)

    logger.info(f"{Fore.BLACK}{Back.GREEN}\u2713 UI resistance check complete{Style.RESET_ALL}")


def check_digital():
    set_input_type_all(0)
    expected_result_on = np.array([1] * 8)
    expected_result_off = np.array([0] * 8)
    digital_inputs = np.array([])

    logger.info(f"{Fore.BLACK}{Back.YELLOW}Testing digital inputs, Check inputs set to 10K and ouput set to 12V{Style.RESET_ALL}")

    passed = False
    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Connect inputs to digitalin and outputs to digital out{Style.RESET_ALL}")

        if get_input():
            break
        write_uo_0_12_all(expected_result_on.tolist())
        time.sleep(0.2)
        digital_inputs = np.array(read_ui_digital_all())
        passed = check_Correct(expected_result_on, digital_inputs, 0)
        if not passed:
            continue

        write_uo_0_12_all(expected_result_off.tolist())
        time.sleep(0.2)
        digital_inputs = np.array(read_ui_digital_all())
        passed = check_Correct(expected_result_off, digital_inputs, 0)
        if not passed:
            continue

        write_uo_0_12_all(expected_result_on.tolist())
        time.sleep(0.2)
        digital_inputs = np.array(read_ui_digital_all())
        passed = check_Correct(expected_result_on, digital_inputs, 0)
        if not passed:
            continue

        write_uo_0_12_all(expected_result_off.tolist())
        time.sleep(0.2)
        digital_inputs = np.array(read_ui_digital_all())
        passed = check_Correct(expected_result_off, digital_inputs, 0)
        if not passed:
            continue

        logger.info(f"{Fore.BLACK}{Back.GREEN}\u2713 Digital IO check complete{Style.RESET_ALL}")



def check_pulse():
    set_input_type_all(0)
    expected_result_on = np.array([1] * 8)
    expected_result_off = np.array([0] * 8)
    expected_pulses = np.array([2, 2, 2, 0, 0, 0, 0, 0])
    logger.info(f"{Fore.BLACK}{Back.YELLOW}Testing pulse inputs 1-3, Check inputs set to 10K and ouput set to 12V{Style.RESET_ALL}")

    passed = False

    while not passed:
        set_input_pulse_1_3()
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Connect inputs to digital in and outputs to digital out{Style.RESET_ALL}")

        # input(colored("*** Press enter when ready ***", 'white', 'on_blue'))
        delay = 0.2
        time.sleep(delay)
        write_uo_0_12_all(expected_result_on.tolist())
        time.sleep(delay)
        write_uo_0_12_all(expected_result_off.tolist())
        time.sleep(delay)
        write_uo_0_12_all(expected_result_on.tolist())
        time.sleep(delay)
        write_uo_0_12_all(expected_result_off.tolist())
        passed = check_Correct(expected_pulses, read_ui_pulse_all(), 0)
        if not passed:
            set_input_type_all(0)
            continue

        time.sleep(delay)
        write_uo_0_12_all(expected_result_on.tolist())
        time.sleep(delay)
        write_uo_0_12_all(expected_result_off.tolist())
        time.sleep(delay)
        write_uo_0_12_all(expected_result_on.tolist())
        time.sleep(delay)
        write_uo_0_12_all(expected_result_off.tolist())
        passed = check_Correct(expected_pulses*2, read_ui_pulse_all(), 0)
        if not passed:
            set_input_type_all(0)
            continue

    set_input_type_all(0)
    logger.info(f"{Fore.BLACK}{Back.GREEN}\u2713 Digital pulse 1-3 check complete{Style.RESET_ALL}")


def print_all_the_lines():
    for i in range(20):
        logger.info('')


import json
import os

HIGH_SCORES_FILE = 'high_scores.json'

def load_high_scores():
    if os.path.exists(HIGH_SCORES_FILE):
        with open(HIGH_SCORES_FILE, 'r') as f:
            return json.load(f)
    else:
        return [{'name': None, 'score': float('inf')} for _ in range(3)]

def save_high_scores(high_scores):
    with open(HIGH_SCORES_FILE, 'w') as f:
        json.dump(high_scores, f)

def update_high_scores(new_score):
    high_scores = load_high_scores()
    # Check if the new score is faster than the slowest high score
    if new_score < high_scores[-1]['score']:
        name = input('New high score! Please enter your name: ')
        # Replace the slowest high score with the new score
        high_scores[-1] = {'name': name, 'score': new_score}
        # Sort the high scores from fastest to slowest
        high_scores.sort(key=lambda s: s['score'])
        save_high_scores(high_scores)


def print_high_scores():
    high_scores = load_high_scores()
    print("High Scores:")
    for i, score in enumerate(high_scores, start=1):
        if score['name'] is not None:
            print(f"{i}. {score['name']}: {score['score']} seconds")
        else:
            print(f"{i}. ---")

def flash(filename):
    cmd = f"sudo dfu-util -a 0 -i 0 -s 0x08000000:leave -D {filename}"
    try:
        subprocess.run(cmd, shell=True, check=True, stdout=None, stderr=None)
    except Exception as e:
        print(f"{Fore.WHITE}{Back.RED}Flash command failed with error: {e}{Style.RESET_ALL}")

        return False
    return True


def flash_device():
    global logger
    logger.info(f"{Fore.BLACK}{Back.YELLOW}Uploading firmware:{Style.RESET_ALL}")

    passed = False
    while not passed:
        logger.info(f"{Fore.BLACK}{Back.YELLOW}Set controller into boot mode{Style.RESET_ALL}")

        if get_input():
            logger.info(f"{Fore.BLACK}{Back.YELLOW}Upload Skipped{Style.RESET_ALL}")

            break
        passed = flash('/home/pi/Testing/R-IO-16-Modbus_v4.0.0_F411RE.bin')
        if not passed:
            logger.info(f"{Fore.WHITE}{Back.RED}\u2717 Upload failed{Style.RESET_ALL}")

        logger.info(f"{Fore.BLACK}{Back.YELLOW}Set controller into boot mode{Style.RESET_ALL}")
        if passed:
            logger.info(f"{Fore.WHITE}{Back.GREEN}\u2713 Upload Complete{Style.RESET_ALL}")


def run_test_script(script, args=None):
    try:
        if args is not None:
            # If args is provided, concatenate it with the script
            command = f'python {script} {args}'
        else:
            command = f'python {script}'

        output = subprocess.run(command, shell=True, check=True, stdout=None, stderr=None)

    except subprocess.CalledProcessError as e:
        # Handle the exception or re-raise it if needed
        return e

try:
    #make sure the test output file is clean for each device
    with open('/home/pi/Testing/output.txt', "w") as file:
        file.truncate(0)    
        
    start_time = time.time()
    flash_device()
    time.sleep(2)
    run_test_script("/home/pi/Testing/serial_test.py")
    
    FULL_TEST_SUITE = ['Dips_test', 'Modbus_test', 'lora_test']
    
    unlock_calibrations()
    logger.info(str(read_ui_calib_coeff()))
    logger.info(str(read_ui_calib_offset()))


    factory_reset()
    unlock_calibrations()
    set_input_type_all(0)
    reset_ui_calabration()
    reset_uo_calabration()

    #print_all_the_lines()
    calabrate_UI_raw()
    #print_all_the_lines()
    calabrate_UO_0_10V()
    #print_all_the_lines()
    check_voltage_in_out()
    #print_all_the_lines()
    check_10k_resistance()
    #print_all_the_lines()
    check_digital()
    #print_all_the_lines()
    check_pulse()
    #print_all_the_lines()



    logger.info(f'Tests completed in: {round(time.time() - start_time, 2)}s')
    #update_high_scores(round(time.time() - start_time, 2))
    #print_high_scores()

    FULL_TEST_SUITE += ['UI/IO calib_test', 'UI_raw_test', 'UO_0_10V_test', 'V_in_out_test', 'resistance_test', 'digital_test', 'pulse_test']

    # We only make it to the next lines if all the above tests worked so we can add the test suit as follows
    logger.info(f'Full test suite: {FULL_TEST_SUITE}')

    # Path to the private key file (replace with your actual private key file path)
    private_key_path = '/home/pi/.ssh/new_key'

    # Specify the SSH parameters
    ssh_params = {
        'hostname': '192.168.15.227',
        'username': 'testbench',
        'port': 22,
        'key_filename': private_key_path
    }

    # Create an SSH client using key authentication
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(**ssh_params)

    # Create an SFTP client
    sftp = ssh_client.open_sftp()

    # Upload the file using SFTP
    sftp.put('/home/pi/Testing/output.txt', '/home/testbench/io16-testing/Testing/output.txt')

    # Close the SFTP and SSH clients
    sftp.close()

    # Execute the command on the remote device
    # command = 'sudo python3 /home/testbench/io16-testing/Testing/Flash_And_Test.py'
    # stdin, stdout, stderr = ssh_client.exec_command(command)
    ssh_client.close()
    
except KeyboardInterrupt:
    pass

