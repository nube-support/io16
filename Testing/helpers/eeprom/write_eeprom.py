from smbus2 import SMBus
import time
from datetime import datetime

I2C_BUS = 1  # Usually 1 for Raspberry Pi, but may vary
EEPROM_ADDRESS = 0x50  # Replace with the correct address for your EEPROM

def write_eeprom(address, data):
    """Write data to EEPROM."""
    with SMBus(I2C_BUS) as bus:
        block_address = EEPROM_ADDRESS | ((address >> 8) & 0x07)
        byte_address = address & 0xFF
        for i in range(len(data)):
            bus.write_byte_data(block_address, byte_address + i, data[i])
            time.sleep(0.01)

def read_eeprom(address, length):
    """Read data from EEPROM."""
    with SMBus(I2C_BUS) as bus:
        block_address = EEPROM_ADDRESS | ((address >> 8) & 0x07)
        byte_address = address & 0xFF
        data = []
        for i in range(length):
            data.append(bus.read_byte_data(block_address, byte_address + i))
    return bytes(data).decode('utf-8').rstrip('\0')


def set_all_to_FF():
    for addr in range(0, 101):  # Looping from address 0 to 100
        write_eeprom(addr, [255])  # 255 is 0xFF in hexadecimal


import argparse

def main():
    parser = argparse.ArgumentParser(description='Handle EEPROM data')

    parser.add_argument('-o', '--manufacturing_order', required=True, help='Manufacturing Order')
    parser.add_argument('-b', '--barcode', required=True, help='Barcode')
    parser.add_argument('-ma', '--make', required=True, help='Make ID')
    parser.add_argument('-mo', '--model', required=True, help='Model number')
    parser.add_argument('-hw', '--hardware_version', required=True, help='Hardware version')
    parser.add_argument('-ba', '--batch', required=True, help='Batch number')
    parser.add_argument('-date', '--date', required=True, help='Date as UNIX timestamp')
    parser.add_argument('-te', '--technician', required=True, help='Technician name')

    args = parser.parse_args()

    set_all_to_FF()

    # Pad or truncate each argument to fit its designated length
    manufacturing_order_data = args.manufacturing_order.encode('utf-8').ljust(7, b'\0')[:7]
    barcode_data = args.barcode.encode('utf-8').ljust(14, b'\0')[:14]
    make_data = args.make.encode('utf-8').ljust(2, b'\0')[:2]
    model_data = args.model.encode('utf-8').ljust(2, b'\0')[:2]
    hw_data = args.hardware_version.encode('utf-8').ljust(5, b'\0')[:5]
    batch_data = args.batch.encode('utf-8').ljust(4, b'\0')[:4]
    date_data = args.date.encode('utf-8').ljust(10, b'\0')[:10]
    technician_data = args.technician.encode('utf-8').ljust(15, b'\0')[:15]

    # Write each field to EEPROM at specified address
    write_eeprom(0, manufacturing_order_data)
    write_eeprom(7, barcode_data)
    write_eeprom(21, make_data)
    write_eeprom(23, model_data)
    write_eeprom(27, hw_data)
    write_eeprom(32, batch_data)
    write_eeprom(36, date_data)
    write_eeprom(46, technician_data)

    # Reading data from EEPROM
    print("EEPROM Data:")
    print(" Manufacturing Order:", read_eeprom(0, 7).rstrip('\0'))
    print(" Barcode:", read_eeprom(7, 14).rstrip('\0'))
    print(" Make:", read_eeprom(21, 2).rstrip('\0'))
    print(" Model:", read_eeprom(23, 2).rstrip('\0'))
    print(" Hardware Version:", read_eeprom(27, 5).rstrip('\0'))
    print(" Batch:", read_eeprom(32, 4).rstrip('\0'))
    timestamp_str = read_eeprom(36, 10).rstrip('\0')
    timestamp = int(timestamp_str)
    dt_object = datetime.fromtimestamp(timestamp)
    formatted_time = dt_object.strftime("%Y-%m-%d %H:%M:%S")
    print(" Date:", formatted_time)
    print(" Technician:", read_eeprom(46, 15).rstrip('\0'))

if __name__ == '__main__':
    main()