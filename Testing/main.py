import argparse
import time

from pymodbus.client import ModbusSerialClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse


parser = argparse.ArgumentParser()
parser.add_argument('-p', '--port', metavar='port', type=str,
                    help='Serial port', default='/dev/ttyUSB0')
parser.add_argument('-b', '--baud', metavar='baud', type=int,
                    help='Serial baudrate', default=38400)
parser.add_argument('-a', '--address', metavar='address', type=int,
                    help='Modbus address of DUT', default=1)
parser.add_argument('-s', '--slave-address', metavar='address', type=int,
                    help='Modbus address of slave device', default=64)
parser.add_argument('-m', '--model', metavar='MODEL_NUM', type=int,
                    choices=[10, 13, 16, 240], help='R-IO model number', default=16)

args = parser.parse_args()

dut_addr = args.address
slv_addr = args.slave_address
mb_client = ModbusSerialClient(args.port, baudrate=args.baud, timeout=0.25)
builder = BinaryPayloadBuilder(
    byteorder=Endian.Big, wordorder=Endian.Little)


if args.model == 10:
    UO_COUNT = 2
    UI_COUNT = 6
    DO_COUNT = 2
elif args.model == 13:
    UO_COUNT = 5
    UI_COUNT = 6
    DO_COUNT = 2
elif args.model == 16:
    UO_COUNT = 8
    UI_COUNT = 8
    DO_COUNT = 0
elif args.model == 240:
    UO_COUNT = 0
    UI_COUNT = 0
    DO_COUNT = 0


UO_0_10_ACCEPTED_ERROR = 1


def check_ok(rr):
    assert not rr.isError()
    assert not isinstance(rr, ExceptionResponse)
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


def test_do_addrs():
    if not DO_COUNT:
        return
    builder.reset()
    # DOs
    # READ
    # single regs
    offset = 500
    for i in range(DO_COUNT):
        check_ok(mb_client.read_coils(
            address=i+offset, count=1, slave=dut_addr))
    # all DOs
    check_ok(mb_client.read_coils(
        address=0+offset, count=DO_COUNT, slave=dut_addr))
    # too many regs
    check_addr_err(mb_client.read_coils(
        address=0+offset, count=DO_COUNT+1, slave=dut_addr))
    check_addr_err(mb_client.read_coils(
        address=1+offset, count=DO_COUNT, slave=dut_addr))
    check_addr_err(mb_client.read_coils(
        address=DO_COUNT-1+offset, count=2, slave=dut_addr))

    # WRITE
    for i in range(DO_COUNT):
        check_ok(mb_client.write_coil(
            address=i+offset, value=0, slave=dut_addr))
    # all DOs
    check_ok(mb_client.write_coils(
        address=0+offset, values=[0]*DO_COUNT, slave=dut_addr))
    # single out of range
    check_addr_err(mb_client.write_coil(
        address=DO_COUNT+offset, value=0, slave=dut_addr))
    # too many regs
    check_addr_err(mb_client.write_coils(
        address=0+offset, values=[0]*(DO_COUNT+1), slave=dut_addr))
    check_addr_err(mb_client.write_coils(
        address=1+offset, values=[0]*DO_COUNT, slave=dut_addr))
    check_addr_err(mb_client.write_coils(
        address=DO_COUNT-1+offset, values=[0]*2, slave=dut_addr))


def test_uo_coil_addrs():
    builder.reset()
    # UOs
    # single regs
    for i in range(UO_COUNT):
        check_ok(mb_client.read_coils(
            address=i, count=1, slave=dut_addr))
    # all UOs
    check_ok(mb_client.read_coils(
        address=0, count=UO_COUNT, slave=dut_addr))
    # too many regs
    check_addr_err(mb_client.read_coils(
        address=0, count=UO_COUNT+1, slave=dut_addr))
    check_addr_err(mb_client.read_coils(
        address=1, count=UO_COUNT, slave=dut_addr))
    check_addr_err(mb_client.read_coils(
        address=UO_COUNT-1, count=2, slave=dut_addr))

    for i in range(UO_COUNT):
        check_ok(mb_client.write_coil(
            address=i, value=0, slave=dut_addr))
    # all UOs
    check_ok(mb_client.write_coils(
        address=0, values=[0]*UO_COUNT, slave=dut_addr))
    # single out of range
    check_addr_err(mb_client.write_coil(
        address=UO_COUNT, value=0, slave=dut_addr))
    # too many regs
    check_addr_err(mb_client.write_coils(
        address=0, values=[0]*(UO_COUNT+1), slave=dut_addr))
    check_addr_err(mb_client.write_coils(
        address=1, values=[0]*UO_COUNT, slave=dut_addr))
    check_addr_err(mb_client.write_coils(
        address=UO_COUNT-1, values=[0]*2, slave=dut_addr))


def test_ui_addrs():
    builder.reset()
    for offset, size in [(0, 1), (100, 2), (200, 1), (300, 1), (400, 2), (800, 2), (900, 2)]:
        # single regs
        for i in range(UI_COUNT):
            check_ok(mb_client.read_input_registers(
                address=addr(i, size)+offset, count=1*size, slave=dut_addr))
        # all UIs
        check_ok(mb_client.read_input_registers(
            address=0+offset, count=UI_COUNT*size, slave=dut_addr))
        # single out of range
        check_addr_err(mb_client.read_input_registers(
            address=UI_COUNT, count=1, slave=dut_addr))
        # too many regs
        check_addr_err(mb_client.read_input_registers(
            address=0+offset, count=UI_COUNT*size+(1*size), slave=dut_addr))
        check_addr_err(mb_client.read_input_registers(
            address=1+offset, count=UI_COUNT*size, slave=dut_addr))
        check_addr_err(mb_client.read_input_registers(
            address=addr(UI_COUNT-1, size)+offset, count=2*size, slave=dut_addr))
        if size == 2:
            # reading half regs
            for i in range(UI_COUNT):
                check_addr_err(mb_client.read_input_registers(
                    address=addr(i, size)+offset, count=1, slave=dut_addr))
                check_addr_err(mb_client.read_input_registers(
                    address=addr(i, size)+1+offset, count=1, slave=dut_addr))
                check_addr_err(mb_client.read_input_registers(
                    address=addr(i, size)+1+offset, count=2, slave=dut_addr))


def test_uo_hold_addrs():
    builder.reset()
    for offset, size in [(0, 1), (800, 2), (900, 2)]:
        # single regs
        for i in range(UO_COUNT):
            check_ok(mb_client.read_holding_registers(
                address=addr(i, size)+offset, count=1*size, slave=dut_addr))
        # all UOs
        check_ok(mb_client.read_holding_registers(
            address=0+offset, count=UO_COUNT*size, slave=dut_addr))
        # single out of range
        check_addr_err(mb_client.read_holding_registers(
            address=UO_COUNT, count=1, slave=dut_addr))
        # too many regs
        check_addr_err(mb_client.read_holding_registers(
            address=0+offset, count=UO_COUNT*size+(1*size), slave=dut_addr))
        check_addr_err(mb_client.read_holding_registers(
            address=1+offset, count=UO_COUNT*size, slave=dut_addr))
        check_addr_err(mb_client.read_holding_registers(
            address=addr(UO_COUNT-1, size)+offset, count=2*size, slave=dut_addr))
        if size == 2:
            # reading half regs
            for i in range(UO_COUNT):
                check_addr_err(mb_client.read_holding_registers(
                    address=addr(i, size)+offset, count=1, slave=dut_addr))
                check_addr_err(mb_client.read_holding_registers(
                    address=addr(i, size)+1+offset, count=1, slave=dut_addr))
                check_addr_err(mb_client.read_holding_registers(
                    address=addr(i, size)+1+offset, count=2, slave=dut_addr))

    for offset, size in [(0, 1), (800, 2), (900, 2)]:
        # single regs
        for i in range(UO_COUNT):
            check_ok(mb_client.write_registers(
                address=addr(i, size)+offset, values=[0]*(1*size), slave=dut_addr))
        # all UOs
        check_ok(mb_client.write_registers(
            address=0+offset, values=[0]*(UO_COUNT*size), slave=dut_addr))
        # single out of range
        check_addr_err(mb_client.write_register(
            address=UO_COUNT, value=0, slave=dut_addr))
        # too many regs
        check_addr_err(mb_client.write_registers(
            address=0+offset, values=[0]*(UO_COUNT*size+(1*size)), slave=dut_addr))
        check_addr_err(mb_client.write_registers(
            address=1+offset, values=[0]*(UO_COUNT*size), slave=dut_addr))
        check_addr_err(mb_client.write_registers(
            address=addr(UO_COUNT-1, size)+offset, values=[0]*(2*size), slave=dut_addr))
        if size == 2:
            # reading half regs
            for i in range(UO_COUNT):
                check_addr_err(mb_client.write_register(
                    address=addr(i, size)+offset, value=0, slave=dut_addr))
                check_addr_err(mb_client.write_register(
                    address=addr(i, size)+1+offset, value=0, slave=dut_addr))
                check_addr_err(mb_client.write_registers(
                    address=addr(i, size)+1+offset, values=[0]*2, slave=dut_addr))


def test_global_conf_addrs():
    builder.reset()
    offset = 10000
    check_ok(mb_client.read_holding_registers(
        address=0+offset, count=1, slave=dut_addr))
    check_ok(mb_client.read_holding_registers(
        address=17+offset, count=1, slave=dut_addr))
    check_ok(mb_client.read_holding_registers(
        address=0+offset, count=18, slave=dut_addr))
    # single out of range
    check_addr_err(mb_client.read_holding_registers(
        address=18+offset, count=1, slave=dut_addr))
    check_addr_err(mb_client.read_holding_registers(
        address=0+offset-1, count=1, slave=dut_addr))
    # too many
    check_addr_err(mb_client.read_holding_registers(
        address=0+offset, count=19, slave=dut_addr))
    check_addr_err(mb_client.read_holding_registers(
        address=1+offset, count=18, slave=dut_addr))
    check_addr_err(mb_client.read_holding_registers(
        address=17+offset, count=2, slave=dut_addr))
    # write single out of range
    check_addr_err(mb_client.write_registers(
        address=18+offset, values=[0], slave=dut_addr))
    check_addr_err(mb_client.write_registers(
        address=0+offset-1, values=[0], slave=dut_addr))
    check_ok(mb_client.write_register(  # enable persistence reg
        address=offset+5, value=1, slave=dut_addr))
    check_addr_err(mb_client.write_register(
        address=offset+4, value=1, slave=dut_addr))
    check_ok(mb_client.write_register(  # wd time
        address=offset+13, value=60, slave=dut_addr))
    check_addr_err(mb_client.write_register(  # lora rssi
        address=offset+14, value=1, slave=dut_addr))
    check_addr_err(mb_client.write_register(  # lora snr
        address=offset+15, value=1, slave=dut_addr))
    check_ok(mb_client.write_register(  # lora pub enable
        address=offset+16, value=0, slave=dut_addr))

    offset = 10100
    check_ok(mb_client.read_holding_registers(
        address=0+offset, count=1, slave=dut_addr))
    check_ok(mb_client.read_holding_registers(
        address=4+offset, count=1, slave=dut_addr))
    check_ok(mb_client.read_holding_registers(
        address=0+offset, count=5, slave=dut_addr))
    # single out of range
    check_addr_err(mb_client.read_holding_registers(
        address=5+offset, count=1, slave=dut_addr))
    check_addr_err(mb_client.read_holding_registers(
        address=0+offset-1, count=1, slave=dut_addr))
    # too many
    check_addr_err(mb_client.read_holding_registers(
        address=0+offset, count=6, slave=dut_addr))
    check_addr_err(mb_client.read_holding_registers(
        address=1+offset, count=5, slave=dut_addr))
    check_addr_err(mb_client.read_holding_registers(
        address=4+offset, count=2, slave=dut_addr))
    # write single out of range
    check_addr_err(mb_client.write_registers(
        address=7+offset, values=[0], slave=dut_addr))
    check_addr_err(mb_client.write_registers(
        address=0+offset-1, values=[0], slave=dut_addr))


def test_ui_config_addrs():
    builder.reset()
    offset = 5200
    # single regs
    for i in range(UI_COUNT):
        check_ok(mb_client.read_holding_registers(
            address=i+offset, count=1, slave=dut_addr))
    # all UIs
    check_ok(mb_client.read_holding_registers(
        address=0+offset, count=UI_COUNT, slave=dut_addr))
    # out of range
    check_addr_err(mb_client.read_holding_registers(
        address=UI_COUNT, count=1, slave=dut_addr))
    check_addr_err(mb_client.read_holding_registers(
        address=offset-1, count=1, slave=dut_addr))
    check_addr_err(mb_client.read_holding_registers(
        address=offset-1, count=2, slave=dut_addr))
    # too many regs
    check_addr_err(mb_client.read_holding_registers(
        address=0+offset, count=UI_COUNT+1, slave=dut_addr))
    check_addr_err(mb_client.read_holding_registers(
        address=1+offset, count=UI_COUNT, slave=dut_addr))
    check_addr_err(mb_client.read_holding_registers(
        address=UI_COUNT-1+offset, count=2, slave=dut_addr))

    # single regs
    for i in range(UI_COUNT):
        check_ok(mb_client.write_registers(
            address=i+offset, values=[0], slave=dut_addr))
    # all UIs
    check_ok(mb_client.write_registers(
        address=0+offset, values=[0]*UI_COUNT, slave=dut_addr))
    # out of range
    check_addr_err(mb_client.write_register(
        address=UI_COUNT, value=0, slave=dut_addr))
    check_addr_err(mb_client.write_register(
        address=offset-1, value=0, slave=dut_addr))
    check_addr_err(mb_client.write_registers(
        address=offset-1, values=[0]*2, slave=dut_addr))
    # too many regs
    check_addr_err(mb_client.write_registers(
        address=0+offset, values=[0]*(UI_COUNT+1), slave=dut_addr))
    check_addr_err(mb_client.write_registers(
        address=1+offset, values=[0]*UI_COUNT, slave=dut_addr))
    check_addr_err(mb_client.write_registers(
        address=UI_COUNT-1+offset, values=[0]*2, slave=dut_addr))


def test_uo_config_addrs():
    builder.reset()
    offset = 5000
    # single regs
    for i in range(UO_COUNT):
        check_ok(mb_client.read_holding_registers(
            address=i+offset, count=1, slave=dut_addr))
    # all UOs
    check_ok(mb_client.read_holding_registers(
        address=0+offset, count=UO_COUNT, slave=dut_addr))
    # out of range
    check_addr_err(mb_client.read_holding_registers(
        address=UO_COUNT, count=1, slave=dut_addr))
    check_addr_err(mb_client.read_holding_registers(
        address=offset-1, count=1, slave=dut_addr))
    check_addr_err(mb_client.read_holding_registers(
        address=offset-1, count=2, slave=dut_addr))
    # too many regs
    check_addr_err(mb_client.read_holding_registers(
        address=0+offset, count=UO_COUNT+1, slave=dut_addr))
    check_addr_err(mb_client.read_holding_registers(
        address=1+offset, count=UO_COUNT, slave=dut_addr))
    check_addr_err(mb_client.read_holding_registers(
        address=UO_COUNT-1+offset, count=2, slave=dut_addr))

    # single regs
    for i in range(UO_COUNT):
        check_ok(mb_client.write_registers(
            address=i+offset, values=[0], slave=dut_addr))
    # all UOs
    check_ok(mb_client.write_registers(
        address=0+offset, values=[0]*UO_COUNT, slave=dut_addr))
    # out of range
    check_addr_err(mb_client.write_register(
        address=UO_COUNT, value=0, slave=dut_addr))
    check_addr_err(mb_client.write_register(
        address=offset-1, value=0, slave=dut_addr))
    check_addr_err(mb_client.write_registers(
        address=offset-1, values=[0]*2, slave=dut_addr))
    # too many regs
    check_addr_err(mb_client.write_registers(
        address=0+offset, values=[0]*(UO_COUNT+1), slave=dut_addr))
    check_addr_err(mb_client.write_registers(
        address=1+offset, values=[0]*UO_COUNT, slave=dut_addr))
    check_addr_err(mb_client.write_registers(
        address=UO_COUNT-1+offset, values=[0]*2, slave=dut_addr))


def test_ui_config_values():
    builder.reset()
    offset = 5200
    values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    # all values individually
    for i in range(UI_COUNT):
        for v in values:
            check_ok(mb_client.write_register(
                address=i+offset, value=v, slave=dut_addr))
            value = get_uint16(mb_client.read_holding_registers(
                address=i+offset, count=1, slave=dut_addr))
            assert(value == v)
            check_ok(mb_client.write_register(
                address=i+offset, value=0, slave=dut_addr))
    # write multiple
    check_ok(mb_client.write_registers(
        address=offset, values=values[:UI_COUNT], slave=dut_addr))
    decoder = get_decoder(check_ok(mb_client.read_holding_registers(
        address=offset, count=UI_COUNT, slave=dut_addr)))
    for i in range(UI_COUNT):
        assert(decoder.decode_16bit_uint() == values[i])

    # write multiple with reset
    check_ok(mb_client.write_registers(
        address=offset, values=values[:UI_COUNT], slave=dut_addr))
    soft_reset()
    decoder = get_decoder(check_ok(mb_client.read_holding_registers(
        address=offset, count=UI_COUNT, slave=dut_addr)))
    for i in range(UI_COUNT):
        assert(decoder.decode_16bit_uint() == values[i])

    # values out of range
    check_slave_err(mb_client.write_register(
        address=0+offset, value=10, slave=dut_addr))
    builder.add_16bit_int(-1)
    regs = builder.to_registers()
    check_slave_err(mb_client.write_registers(
        0+offset, regs, slave=dut_addr))

    # reset
    check_ok(mb_client.write_registers(
        address=0+offset, values=[0]*UI_COUNT, slave=dut_addr))


def test_uo_config_values():
    builder.reset()
    offset = 5000
    values = [0, 1, 2]
    # all values individually
    for i in range(UO_COUNT):
        for v in values:
            check_ok(mb_client.write_register(
                address=i+offset, value=v, slave=dut_addr))
            value = get_uint16(mb_client.read_holding_registers(
                address=i+offset, count=1, slave=dut_addr))
            assert(value == v)
    # write multiple
    check_ok(mb_client.write_registers(
        address=offset, values=[1]*UO_COUNT, slave=dut_addr))
    decoder = get_decoder(check_ok(mb_client.read_holding_registers(
        address=offset, count=UO_COUNT, slave=dut_addr)))
    for i in range(UO_COUNT):
        assert(decoder.decode_16bit_uint() == 1)

    # write multiple with reset
    check_ok(mb_client.write_registers(
        address=offset, values=[1]*UO_COUNT, slave=dut_addr))
    soft_reset()
    decoder = get_decoder(check_ok(mb_client.read_holding_registers(
        address=offset, count=UO_COUNT, slave=dut_addr)))
    for i in range(UO_COUNT):
        assert(decoder.decode_16bit_uint() == 1)

    # values out of range
    check_slave_err(mb_client.write_register(
        address=0+offset, value=10, slave=dut_addr))
    builder.add_16bit_int(-1)
    regs = builder.to_registers()
    check_slave_err(mb_client.write_registers(
        0+offset, regs, slave=dut_addr))

    # reset
    check_ok(mb_client.write_registers(
        address=0+offset, values=[0]*UO_COUNT, slave=dut_addr))


def test_uo_write_values_0_10():
    builder.reset()
    # all UO
    for i in range(UO_COUNT):
        v = 550
        check_ok(mb_client.write_register(
            address=i, value=v, slave=dut_addr))
        value = get_uint16(mb_client.read_holding_registers(
            address=i, count=1, slave=dut_addr))
        assert(abs(value-v) <= UO_0_10_ACCEPTED_ERROR)
        value = get_float(mb_client.read_holding_registers(
            address=addr(i, 2)+900, count=2, slave=dut_addr))
        assert(abs(value-(v/1000)) <= UO_0_10_ACCEPTED_ERROR)
        # typed and raw
        for offset, mult in [(800, 100), (900, 1000)]:
            builder.reset()
            builder.add_32bit_float(v/mult)
            check_ok(mb_client.write_registers(
                addr(i, 2)+offset, builder.to_registers(), slave=dut_addr))
            value = get_uint16(mb_client.read_holding_registers(
                address=i, count=1, slave=dut_addr))
            assert(abs(value-v) <= UO_0_10_ACCEPTED_ERROR)
            value = get_float(mb_client.read_holding_registers(
                address=addr(i, 2)+offset, count=2, slave=dut_addr))
            assert(abs(value-(v/mult)) <= UO_0_10_ACCEPTED_ERROR)

    # all values
    for v in range(11):
        v *= 10
        for j in range(10):
            v += j
            if v > 1000:
                v = 1000
            check_ok(mb_client.write_register(
                address=0, value=v, slave=dut_addr))
            value = get_uint16(mb_client.read_holding_registers(
                address=0, count=1, slave=dut_addr))
            assert(abs(value-v) <= UO_0_10_ACCEPTED_ERROR)

    # write multiple
    for v in [110, 650, 920]:
        check_ok(mb_client.write_registers(
            address=0, values=[v]*UO_COUNT, slave=dut_addr))
        decoder = get_decoder(check_ok(mb_client.read_holding_registers(
            address=0, count=UO_COUNT, slave=dut_addr)))
        for i in range(UO_COUNT):
            assert(abs(decoder.decode_16bit_uint() - v)
                   <= UO_0_10_ACCEPTED_ERROR)

    # write multiple with reset
    values = [110, 220, 330, 440, 550, 660, 770, 880, 990, 1000]
    check_ok(mb_client.write_registers(
        address=0, values=values[:UO_COUNT], slave=dut_addr))
    soft_reset()
    decoder = get_decoder(check_ok(mb_client.read_holding_registers(
        address=0, count=UO_COUNT, slave=dut_addr)))
    for i in range(UO_COUNT):
        v = decoder.decode_16bit_uint()
        assert(abs(v - values[i]) <= UO_0_10_ACCEPTED_ERROR)

    # typed point
    decoder = get_decoder(check_ok(mb_client.read_holding_registers(
        address=5000, count=UO_COUNT, slave=dut_addr)))
    for i in range(UO_COUNT):
        v = decoder.decode_16bit_uint()
        assert(v == 1)
    # typed and raw point
    for offset, mult in [(800, 100), (900, 1000)]:
        builder.reset()
        # typed and raw point read
        values = [110, 220, 330, 440, 550, 660, 770, 880, 990, 1000]
        check_ok(mb_client.write_registers(
            address=0, values=values[:UO_COUNT], slave=dut_addr))
        decoder = get_decoder(check_ok(mb_client.read_holding_registers(
            address=offset, count=UO_COUNT*2, slave=dut_addr)))
        for i in range(UO_COUNT):
            v = decoder.decode_32bit_float()
            assert(abs(v - (values[i]/mult)) <= UO_0_10_ACCEPTED_ERROR/mult)
        # typed point write
        for v in values[:UO_COUNT]:
            builder.add_32bit_float(v/mult)
        regs = builder.to_registers()
        check_ok(mb_client.write_registers(offset, regs, slave=dut_addr))
        decoder = get_decoder(check_ok(mb_client.read_holding_registers(
            address=0, count=UO_COUNT, slave=dut_addr)))
        for i in range(UO_COUNT):
            v = decoder.decode_16bit_uint()
            assert(abs(v - values[i]) <= UO_0_10_ACCEPTED_ERROR)
    builder.reset()

    # values out of range
    check_slave_err(mb_client.write_register(
        address=0, value=1001, slave=dut_addr))
    builder.add_16bit_int(-1)
    regs = builder.to_registers()
    check_slave_err(mb_client.write_registers(
        0, regs, slave=dut_addr))
    # typed
    builder.reset()
    builder.add_32bit_float(10.01)
    check_slave_err(mb_client.write_registers(
        800, builder.to_registers(), slave=dut_addr))
    # raw
    builder.reset()
    builder.add_32bit_float(1.01)
    check_slave_err(mb_client.write_registers(
        900, builder.to_registers(), slave=dut_addr))

    # reset
    check_ok(mb_client.write_registers(
        address=900, values=[0]*UO_COUNT*2, slave=dut_addr))


def test_uo_write_values_coil():
    builder.reset()
    # reset
    check_ok(mb_client.write_coils(
        address=0, values=[False]*UO_COUNT, slave=dut_addr))
    # all UO
    for v in [True, False]:
        for i in range(UO_COUNT):
            check_ok(mb_client.write_coil(
                address=i, value=v, slave=dut_addr))
            value = mb_client.read_coils(
                address=i, count=1, slave=dut_addr).bits[0]
            assert(value == v)
            value = get_float(mb_client.read_holding_registers(
                address=addr(i, 2)+900, count=2, slave=dut_addr))
            assert(value == float(v))
            # typed and raw
            for offset in [800, 900]:
                builder.reset()
                builder.add_32bit_float(float(v))
                check_ok(mb_client.write_registers(
                    addr(i, 2)+offset, builder.to_registers(), slave=dut_addr))
                value = mb_client.read_coils(
                    address=i, count=1, slave=dut_addr).bits[0]
                assert(value == float(v))

    # reset
    check_ok(mb_client.write_coils(
        address=0, values=[False]*UO_COUNT, slave=dut_addr))

    # write multiple
    values = [True, False, True, False, True, False, True, False, True, False]
    check_ok(mb_client.write_coils(
        address=0, values=values[:UO_COUNT], slave=dut_addr))
    bits = check_ok(mb_client.read_coils(
        address=0, count=UO_COUNT, slave=dut_addr)).bits
    assert(bits[:UO_COUNT] == values[:UO_COUNT])
    # reset
    check_ok(mb_client.write_coils(
        address=0, values=[False]*UO_COUNT, slave=dut_addr))
    # write multiple with reset
    check_ok(mb_client.write_coils(
        address=0, values=values[:UO_COUNT], slave=dut_addr))
    soft_reset()
    bits = check_ok(mb_client.read_coils(
        address=0, count=UO_COUNT, slave=dut_addr)).bits
    assert(bits[:UO_COUNT] == values[:UO_COUNT])

    # reset
    check_ok(mb_client.write_coils(
        address=0, values=[False]*UO_COUNT, slave=dut_addr))

    # typed point
    decoder = get_decoder(check_ok(mb_client.read_holding_registers(
        address=5000, count=UO_COUNT, slave=dut_addr)))
    for i in range(UO_COUNT):
        v = decoder.decode_16bit_uint()
        assert(v == 2)
    # typed and raw point
    for offset, _ in [(800, 100), (900, 1000)]:
        # reset
        check_ok(mb_client.write_coils(
            address=0, values=[False]*UO_COUNT, slave=dut_addr))
        builder.reset()
        # typed and raw point read
        values = [True, False, True, False, True,
                  False, True, False, True, False]
        check_ok(mb_client.write_coils(
            address=0, values=values[:UO_COUNT], slave=dut_addr))
        decoder = get_decoder(check_ok(mb_client.read_holding_registers(
            address=offset, count=UO_COUNT*2, slave=dut_addr)))
        for i in range(UO_COUNT):
            v = decoder.decode_32bit_float()
            assert(v == float(values[i]))
        # typed point write
        # reset
        check_ok(mb_client.write_coils(
            address=0, values=[False]*UO_COUNT, slave=dut_addr))
        for v in values[:UO_COUNT]:
            builder.add_32bit_float(float(v))
        regs = builder.to_registers()
        check_ok(mb_client.write_registers(offset, regs, slave=dut_addr))
        bits = check_ok(mb_client.read_coils(
            address=0, count=UO_COUNT, slave=dut_addr)).bits
        assert(bits[:UO_COUNT] == values[:UO_COUNT])
        builder.reset()

    # reset
    check_ok(mb_client.write_coils(
        address=0, values=[False]*UO_COUNT, slave=dut_addr))

    # values out of range
    # typed
    builder.reset()
    builder.add_32bit_float(1.01)
    check_slave_err(mb_client.write_registers(
        800, builder.to_registers(), slave=dut_addr))
    # raw
    builder.reset()
    builder.add_32bit_float(1.01)
    check_slave_err(mb_client.write_registers(
        900, builder.to_registers(), slave=dut_addr))

    # reset
    check_ok(mb_client.write_coils(
        address=0, values=[False]*UO_COUNT, slave=dut_addr))


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
    print(f'{bcolors.GREEN}  PASSED{bcolors.ENDC}')


try:
    start_time = time.time()
    mb_client.connect()

    test(test_ui_addrs)
    test(test_do_addrs)
    test(test_uo_coil_addrs)
    test(test_uo_hold_addrs)
    test(test_ui_config_addrs)
    test(test_uo_config_addrs)
    test(test_global_conf_addrs)
    test(test_ui_config_values)
    test(test_uo_config_values)
    test(test_uo_write_values_0_10)
    test(test_uo_write_values_coil)

    print()
    print(f'{bcolors.BOLD}{bcolors.GREEN}PASSED{bcolors.ENDC}')
    print(f'Tests completed in: {round(time.time()-start_time, 2)}s')


finally:
    mb_client.close()


