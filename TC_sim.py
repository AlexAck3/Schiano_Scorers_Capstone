import random as r
import time as t

class Thermocouple:
    def __init__(self, error, temp):
        self.error = error
        self.temp = temp
    
    def getTemp(self):
        return self.temp

    def getError(self):
        return self.error

    def setTemP(self, temp):
        self.temp = temp
        return self.temp

    def setError(self, error):
        self.error = error
        return self.error


x = Thermocouple(1, 32)
rand

while 1:
    print(x.getTemp())
    t.sleep(0.1)