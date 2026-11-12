'''
SETUP

Step 1 - Activate SPI (It's off by default)
https://learn.sparkfun.com/tutorials/raspberry-pi-spi-and-i2c-tutorial/all#spi-on-pi
    - Just do the Desktop GUI steps

Step 2 - Install everything for TC AMPs
    Install Python Packages
    https://learn.adafruit.com/adafruit-max31856-thermocouple-amplifier/python-circuitpython#python-installation-of-max31856-library-3042593
        pip3 install adafruit-circuitpython-max31856    

Step 3 - Install everything for IR Camera
    https://shillehtek.com/blogs/shillehtek-product-manuals/gy-906-mlx90614-baa-non-touch-infrared-temperature-sensor#manual-section-5
    Install: pip install smbus2 mlx90614

#chat firmly believes the package pymlx90614 is the solution to this not wokring
    
    
    '''

# NOTE: ALL TEMPERATURE READINGS ARE IN C NOT F

SPI = 0
I2C = 1
BOTH = 2
PWM = 3
# ------ PWM Options ------
PWM_PERIOD = 5      # s
PWM_DUTYCYCLE = 50  # %
TOP_COIL_PCT = 50   # %
BOT_COIL_PCT = 100 - TOP_COIL_PCT
# -------------------------

SETTING = SPI   # Which one do you want to read?

from smbus2 import SMBus
from mlx90614 import MLX90614
import time

import board
import digitalio

import adafruit_max31856


# I2C - Used for IR Camera 
#   (SDA on Pin 3 [GPIO2]) 
#   (SCL on Pin 5 [GPIO3])
# NOTE: Use "i2cdetect -y 1" to find the value of I2C_ADDR
def Read_I2C():
    bus = SMBus(1)
    sensor = MLX90614(bus, address=0x5A)

    try:
        while True:
            print(f"Ambient: {sensor.get_amb_temp():.2f} C")
            print(f"Object:  {sensor.get_obj_temp():.2f} C")
            print("-" * 30)
            time.sleep(0.5)
    except KeyboardInterrupt:
        bus.close()





# SPI - Used for TC Amps 
#   (SCK on Pin 23 [SCLK]) 
#   (SDO on Pin 21 [MISO]) 
#   (SDI on Pin 19 [MOSI]) 
#   (CS on Pin 24 [CE0])
#   (Ignore 3V_o, FLT, DRDY)
def Read_SPI():
    # Create sensor object, communicating over the board's default SPI bus
    spi = board.SPI()

    # allocate a CS pin and set the direction
    cs = digitalio.DigitalInOut(board.D8)
    cs.direction = digitalio.Direction.OUTPUT
    cs.value = False

    # create a thermocouple object with the above
    thermocouple = adafruit_max31856.MAX31856(spi, cs)

    # print the temperature!
    while True:
        Read_TC(thermocouple)
        time.sleep(0.5)

def Read_TC(tc):
    print("TC Reading")
    print(f"\tObject:\t{tc.temperature:.4F}")
    print("-" * 30)

# Read both SPI and I2C Data
def Read_data():
    try:
        bus = SMBus(1)
        sensor = MLX90614(bus, address=0x5A)

        # Create sensor object, communicating over the board's default SPI bus
        spi = board.SPI()
    
        # allocate a CS pin and set the direction
        cs = digitalio.DigitalInOut(board.D5)
        cs.direction = digitalio.Direction.OUTPUT
    
        # create a thermocouple object with the above
        thermocouple = adafruit_max31856.MAX31856(spi, cs)


        while True:
            print("-" * 30)
            print("IR Reading")
            print(f"\tAmbient:\t{sensor.get_amb_temp():.2f} C")
            print(f"\tObject:\t{sensor.get_obj_temp():.2f} C")
            print("-" * 30)
        
            # print the temperature!
            print("TC Reading")
            print(f"\tObject:\t{thermocouple.temperature}")
            print("-" * 30)

            time.sleep(0.5)

    except KeyboardInterrupt:
        bus.close()

def Run_PWM():
    '''
    PWM Pin for power is GPIO 19
    Coil Select Pin is GPIO 26
    '''
    # Create sensor object, communicating over the board's default SPI bus
    spi = board.SPI()

    # allocate a CS pin and set the direction
    cs = digitalio.DigitalInOut(board.D8)
    cs.direction = digitalio.Direction.OUTPUT
    cs.value = False

    # create a thermocouple object with the above
    thermocouple = adafruit_max31856.MAX31856(spi, cs)

    # The PWM Ratio is the duty cycle/100
    pwm_ratio = (PWM_DUTYCYCLE/100)
    total_on_time = PWM_PERIOD*pwm_ratio
    total_off_time = PWM_PERIOD - total_on_time

    top_coil_time = total_on_time*(TOP_COIL_PCT/100)
    bot_coil_time = total_on_time*(BOT_COIL_PCT/100)

    PWM_pin = digitalio.DigitalInOut(board.D19)

    # False = Top, True = Bottom
    coil_select = digitalio.DigitalInOut(board.D26)

    while True:
        # PWM ON
        PWM_pin.value = True
        print("-" * 30)
        print(f"PWM ON for {total_on_time:2F} seconds")
        print("-" * 30)

        # Switch to top coil
        coil_select.value = False
        print(f"\nTOP COIL: {top_coil_time}s")
        time.sleep(top_coil_time)
        Read_TC()

        # Switch to bottom coil
        coil_select.value = True
        print(f"\nBOTTOM COIL: {bot_coil_time}s")
        time.sleep(bot_coil_time)
        Read_TC()

        # PWM OFF
        PWM_pin.value = False
        print("-" * 30)
        print(f"PWM Off for {total_off_time:2F} seconds")
        print("-" * 30)
        time.sleep(total_off_time)

if __name__ == "__main__":
    if SETTING == SPI:
        Read_SPI()
    elif SETTING == I2C:
        Read_I2C()
    elif SETTING == PWM:
        Run_PWM()
    else:
        Read_data()