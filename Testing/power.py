#
# import vxi11
# import time
# import math
#
#
# instr = vxi11.Instrument("192.168.15.11")
# # instr.timeout = 1
# instr.clear()
# # time.sleep(0.2)
# # instr.close()
# # time.sleep(0.2)
# instr.open()
# time.sleep(0.2)
# # instr.close()
# print(instr.ask("*IDN?"))
#
# # exit()
# # time.sleep(1)
# # instr.open()
# # time.sleep(1)
# # # Simple function to set the voltage
# def set_voltage(channel, voltage):
#     instr.write(":SOUR" + str(channel) + ":VOLT " + str(voltage))
#     time.sleep(0.2)
#
# def channel_out(channel, out):
#     outstr = "ON" if out else "OFF"
#     instr.write(":OUTP CH" + str(channel) + "," + outstr)
#     time.sleep(0.2)
#
#
#
# # # Settings
# # offset = 15.0  # Volts
# # gain = 10  # Volts
# # period = 200  # Seconds
# #
# # set initial voltage and turn on
# set_voltage(1, 2.5)
# channel_out(1, True)
# time.sleep(3)
# set_voltage(1, 7.5)
# time.sleep(3)
# channel_out(1, False)
# instr.abort()
# time.sleep(1)
# instr.close()
# time.sleep(1)
#
# instr.unlock()
# # instr.remote()
# # instr.close()
# # set_voltage(1, offset)
# # time.sleep(5)
# #
# # # initial timestamp
# # initial_timestamp = time.time()
# #
# # while True:
# #     # Calculate x
# #     x = (time.time() - initial_timestamp) * 2 * math.pi / period
# #     # Calculate f(x) = a + b * sin(x) * cos(20x)
# #     Voltage = offset + gain * (math.sin(x) * math.cos(20 * x))
# #     set_voltage(1, round(Voltage, 3))
# #     time.sleep(0.2)
# #     if x > 2 * math.pi:
# #         break
# #
# # # Set final voltage and turn off
# # set_voltage(1, offset)
# # time.sleep(5)
# # instr.write(":OUTP CH1,OFF")



import pyvisa as visa
import time
rm = visa.ResourceManager('@py')
print(rm.list_resources())
instr = rm.open_resource("ASRL/dev/ttyAMA0::INSTR")
print(instr.ask("*IDN?"))

def channel_out(channel, out):
    outstr = "ON" if out else "OFF"
    instr.write(":OUTP CH" + str(channel) + "," + outstr)
    time.sleep(0.2)


# channel_out(1, True)


# import qcodes as qc
# from qcodes.instrument_drivers.rigol import RigolDP832
#
# ps = RigolDP832('ps', 'ASRL/dev/ttyAMA0::INSTR')
# ps.ch1.set_voltage(1)
# ps.ch1.set_current(0.2)
# ps.ch1.state('on')
#
#
# from DP832 import *
#
# try:
#     PSU = DP832()
#     print(PSU.status)
#
# except:
#     print("Connection Failed, Script Ended")
#
# PSU.toggle_output(1, True)
# PSU.set_voltage(1, 13.333)
# print(PSU.measure_current(1))
