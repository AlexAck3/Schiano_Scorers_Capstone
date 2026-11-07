'''
SETUP

Step 1 - Activate SPI (It's off by default)
https://learn.sparkfun.com/tutorials/raspberry-pi-spi-and-i2c-tutorial/all#spi-on-pi
    - Just do the Desktop GUI steps

Step 2 - Install everything for TC AMPs
    Install Adafruit CircuitPython
    https://learn.adafruit.com/adafruit-max31856-thermocouple-amplifier/python-circuitpython#circuitpython-installation-of-max31856-library-3042592

    Install Python Packages
    https://learn.adafruit.com/adafruit-max31856-thermocouple-amplifier/python-circuitpython#python-installation-of-max31856-library-3042593
        pip3 install adafruit-circuitpython-max31856    

Step 3 - Install everything for IR Camera
    Install: pip install smbus2 mlx90614

'''
SPI = 0
I2C = 1
BOTH = 2

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
            print(f"Ambient: {sensor.get_ambient():.2f} C")
            print(f"Object:  {sensor.get_object_1():.2f} C")
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
    cs = digitalio.DigitalInOut(board.D5)
    cs.direction = digitalio.Direction.OUTPUT

    # create a thermocouple object with the above
    thermocouple = adafruit_max31856.MAX31856(spi, cs)

    # print the temperature!
    while True:
        print("TC Reading")
        print(f"\tObject:\t{thermocouple.temperature}")
        print("-" * 30)

        time.sleep(0.5)

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
            print(f"\tAmbient:\t{sensor.get_ambient():.2f} C")
            print(f"\tObject:\t{sensor.get_object_1():.2f} C")
            print("-" * 30)
        
            # print the temperature!
            print("TC Reading")
            print(f"\tObject:\t{thermocouple.temperature}")
            print("-" * 30)

            time.sleep(0.5)

    except KeyboardInterrupt:
        bus.close()

if __name__ == "__main__":
    if SETTING == SPI:
        Read_SPI()
    elif SETTING == I2C:
        Read_I2C()
    else:
        Read_data()