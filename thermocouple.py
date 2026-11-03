import random

class Thermocouple:
    def __init__( self, oven, tau=5.0, noise_std=0.2):

        self.oven = oven
        self.tau = tau
        self.noise_std = noise_std
        self.sensor_temp = oven.air_temp
        self.offset = random.uniform(-2.0, 2.0) #simulates the error of the TC
        #The amplifiers are not considered since they are way better in terms of
        #error than the TC's

    def update(self, dt):

        actual_temp = self.oven.air_temp

        self.sensor_temp += (actual_temp - self.sensor_temp) * dt / self.tau

    def read(self):
        return (self.sensor_temp + self.offset + random.gauss(0, self.noise_std))