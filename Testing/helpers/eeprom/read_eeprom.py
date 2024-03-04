from smbus2 import SMBus
from datetime import datetime

I2C_BUS = 1  # Usually 1 for Raspberry Pi, but may vary
EEPROM_ADDRESS = 0x50  # Replace with the correct address for your EEPROM

def read_eeprom(address, length):
    """Read data from EEPROM."""
    with SMBus(I2C_BUS) as bus:
        block_address = EEPROM_ADDRESS | ((address >> 8) & 0x07)
        byte_address = address & 0xFF
        data = []
        for i in range(length):
            data.append(bus.read_byte_data(block_address, byte_address + i))
    return bytes(data).decode('utf-8').rstrip('\0')


def main():
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
