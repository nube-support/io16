
pin_value = 0.5
getCalibrationCoeff = 1
getCalibrationOffset = 0
pin_value = pin_value * getCalibrationCoeff + getCalibrationOffset
pin_value /= 2.75
print ((10000 * pin_value) / (1 - pin_value));