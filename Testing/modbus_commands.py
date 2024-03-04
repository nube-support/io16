from pymodbus.client import ModbusSerialClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse
import sys
import time

UO_COUNT = 8
UI_COUNT = 8
DO_COUNT = 0

MODB_BAUD = 38400
dut_addr = 1

mb_client = ModbusSerialClient(
    port='/dev/ttyS0', baudrate=MODB_BAUD, timeout=0.25)
builder = BinaryPayloadBuilder(
    byteorder=Endian.Big, wordorder=Endian.Little)


def check_ok(rr):
    try:
        assert not rr.isError()
    except Exception as e:
        print("Error:", str(e))

    try:
        assert not isinstance(rr, ExceptionResponse)
    except Exception as e:
        print("Error:", str(e))

    return rr

def check_err(rr, err):
    assert rr.isError()
    assert isinstance(rr, ExceptionResponse)
    assert rr.exception_code == err
    return rr


def check_addr_err(rr):
    return check_err(rr, 2)


def check_slave_err(rr):
    return check_err(rr, 4)


def addr(a, size) -> int:
    return a * size


def get_decoder(resp) -> BinaryPayloadDecoder:
    return BinaryPayloadDecoder.fromRegisters(
        resp.registers, byteorder=Endian.Big, wordorder=Endian.Little)


def get_int16(resp) -> int:
    return get_decoder(resp).decode_16bit_int()


def get_uint16(resp) -> int:
    return get_decoder(resp).decode_16bit_uint()


def get_int32(resp) -> int:
    return get_decoder(resp).decode_32bit_int()


def get_uint32(resp) -> int:
    return get_decoder(resp).decode_32bit_uint()


def get_float(resp) -> int:
    return get_decoder(resp).decode_32bit_float()


def soft_reset():
    check_ok(mb_client.write_register(
        address=10500, value=1, slave=dut_addr))
    time.sleep(2)

def factory_reset():
    check_ok(mb_client.write_register(
        address=10501, value=1, slave=dut_addr))
    time.sleep(2)


def read_ui_10k(point):
    return get_int16(mb_client.read_input_registers(
        address=point, count=1, slave=dut_addr))


def read_ui_0_10(point):
    return get_int16(mb_client.read_input_registers(
        address=point + 200, count=1, slave=dut_addr))


def read_ui_4_20(point):
    return get_int16(mb_client.read_input_registers(
        address=point + 300, count=1, slave=dut_addr))


def read_ui_0_12(point):
    return check_ok(mb_client.read_discrete_inputs(
        address=point, count=1, slave=dut_addr)).bits[0]


def read_uo_0_12(point):
    return check_ok(mb_client.read_coils(
        address=point, count=1, slave=dut_addr)).bits[0]


def write_uo_0_12(point, value):
    check_ok(mb_client.write_coil(
        address=point, value=value, slave=dut_addr))


def write_uo_0_10(point, value):
    check_ok(mb_client.write_register(
        address=point, value=value, slave=dut_addr))


def read_uo_0_10(point):
    return get_uint16(mb_client.read_holding_registers(
        address=point, count=1, slave=dut_addr))


def read_ui_digital_all():
    resp = check_ok(mb_client.read_discrete_inputs(
        address=0, count=UI_COUNT, slave=dut_addr))
    return resp.bits


def read_ui_10k_all():
    decoder = get_decoder(check_ok(mb_client.read_input_registers(
        address=0, count=UI_COUNT, slave=dut_addr)))
    values = [0] * UI_COUNT
    for i in range(UI_COUNT):
        values[i] = decoder.decode_16bit_int()
    return values


def read_ui_10k_resistance():
    decoder = get_decoder(check_ok(mb_client.read_input_registers(
        address=100, count=UI_COUNT * 2, slave=dut_addr)))
    vals = [0] * UI_COUNT
    for i in range(UI_COUNT):
        vals[i] = decoder.decode_32bit_float()
    return vals


def read_ui_raw_all():
    decoder = get_decoder(check_ok(mb_client.read_input_registers(
        address=900, count=UI_COUNT * 2, slave=dut_addr)))
    vals = [0] * UI_COUNT
    for i in range(UI_COUNT):
        vals[i] = decoder.decode_32bit_float()
    return vals


def read_ui_pulse_all():
    decoder = get_decoder(check_ok(mb_client.read_input_registers(
        address=400, count=UI_COUNT * 2, slave=dut_addr)))
    vals = [0] * UI_COUNT
    for i in range(UI_COUNT):
        vals[i] = decoder.decode_32bit_uint()
    return vals


def read_ui_0_10_all():
    decoder = get_decoder(check_ok(mb_client.read_input_registers(
        address=200, count=UI_COUNT, slave=dut_addr)))
    values = [0] * UI_COUNT
    for i in range(UI_COUNT):
        values[i] = decoder.decode_16bit_uint()
    return values


def read_ui_4_20_all():
    decoder = get_decoder(check_ok(mb_client.read_input_registers(
        address=300, count=UI_COUNT, slave=dut_addr)))
    values = [0] * UI_COUNT
    for i in range(UI_COUNT):
        values[i] = decoder.decode_16bit_uint()
    return values


def read_uo_0_10_all():
    decoder = get_decoder(check_ok(mb_client.read_holding_registers(
        address=0, count=UO_COUNT, slave=dut_addr)))
    values = [0] * UO_COUNT
    for i in range(UO_COUNT):
        values[i] = decoder.decode_16bit_uint()
    return values


def read_uo_0_12_all():
    resp = check_ok(mb_client.read_coils(
        address=0, count=UO_COUNT, slave=dut_addr))
    return resp.bits


def write_uo_0_12_all(values):
    check_ok(mb_client.write_coils(
        address=0, values=values, slave=dut_addr))

def write_uo_0_12_all_delayed(values):
    for i in range(6):
        check_ok(mb_client.write_coil(address=i, value=values[i], slave=dut_addr))
        time.sleep(0.05)


def write_uo_0_10_all(values):
    check_ok(mb_client.write_registers(
        address=0, values=values, slave=dut_addr))


def write_calib(point, value, offset):
    builder.reset()
    builder.add_32bit_float(value)
    check_ok(mb_client.write_registers(
        address=addr(point, 2) + offset, values=builder.to_registers(), slave=dut_addr))


def write_all_UO_calib_coeff(values):
    for i in range(UO_COUNT):
        write_uo_calib_coeff(i, values[i])


def write_all_UO_calib_offset(values):
    for i in range(UO_COUNT):
        write_uo_calib_offset(i, values[i])


def write_uo_calib_coeff(point, value):
    write_calib(point, value, 6000)


def write_uo_calib_offset(point, value):
    write_calib(point, value, 6100)


def write_all_ui_calib_coeff(values):
    for i in range(UI_COUNT):
        write_ui_calib_coeff(i, values[i])


def write_ui_calib_coeff(point, value):
    write_calib(point, value, 6200)


def write_ui_calib_offset(point, value):
    write_calib(point, value, 6300)


def write_all_ui_calib_offset(values):
    for i in range(UI_COUNT):
        write_ui_calib_offset(i, values[i])


def read_calib(offset):
    decoder = get_decoder(check_ok(mb_client.read_holding_registers(
        address=offset, count=UO_COUNT * 2, slave=dut_addr)))
    vals = [0] * 8
    for i in range(8):
        vals[i] = decoder.decode_32bit_float()
    return vals


def read_uo_raw():
    return read_calib(900)


def read_uo_calib_coeff():
    return read_calib(6000)


def read_uo_calib_offset():
    return read_calib(6100)


def read_ui_calib_coeff():
    return read_calib(6200)


def read_ui_calib_offset():
    return read_calib(6300)


def unlock_calibrations():
    check_ok(mb_client.write_register(
        address=10502, value=1, slave=dut_addr))


def set_input_pulse_1_3():
    check_ok(mb_client.write_registers(
        address=5200, values=[8]*3, slave=dut_addr))

def set_input_type_all(type):
    check_ok(mb_client.write_registers(
        address=5200, values=[type]*UI_COUNT, slave=dut_addr))


def set_input_type(type, addr):
    check_ok(mb_client.write_register(
        address=5200+addr-1, value=type, slave=dut_addr))

