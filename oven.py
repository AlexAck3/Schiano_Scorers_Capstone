import random as r

class Oven:
    def __init__(self, temp,):
        self.temp = temp
    
    def getTemp(self):
        return self.temp

    def setTemP(self, temp):
        self.temp = temp
        return self.temp

class HeatingElement:
    def __init__(self, max_power_watts):
        self.max_power = max_power_watts
        self.output = 0.0  # 0-1

    def set_output(self, duty_cycle):
        self.output = max(0.0, min(1.0, duty_cycle))

    @property
    def power(self):
        return self.max_power * self.output

