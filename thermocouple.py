import random

class Thermocouple:
    def __init__(self, tau=5.0, noise_std=0.2, offset_error=random.uniform(-2,2)):
        self.tau = tau
        self.noise_std = noise_std
        self.offset_error = offset_error
        self.oven = oven

        self.temp = 25.0

    def update(self, process_temp, dt):
        self.temp += (process_temp - self.temp) * dt / self.tau

    def read(self):
        return (self.temp + self.offset_error + random.gauss(0, self.noise_std))