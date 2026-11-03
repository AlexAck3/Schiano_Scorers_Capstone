import random
import matplotlib.pyplot as plt



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


    
class HeatingElement:
    def __init__(self, max_power_watts = 1500):
        self.max_power = max_power_watts
        self.output = 0.0   #simulates the duty cycle

    def set_output(self, output):
        self.output = max(0.0, min(1.0, output))

    @property
    def power(self):
        return self.max_power * self.output #returns the max power times the functional duty cycle



class Oven:
    def __init__(self):

        # intial conditions
        self.top_temp = 25.0
        self.air_temp = 25.0
        self.bottom_temp = 25.0
        self.ambient = 25.0

        self.top_element = HeatingElement(1500)
        self.bottom_element = HeatingElement(1500)
        self.tc = Thermocouple(self)

        self.stone_mass = 1000 #CHANGE ME
        self.air_mass = 500 #CHANGE ME

    def update(self, dt):

        # heaters heat stone
        self.top_temp += (self.top_element.power / self.stone_mass) * dt
        self.bottom_temp += (self.bottom_element.power / self.stone_mass) * dt

        # stone heats air
        top_air_transfer = (self.top_temp - self.air_temp) * 0.01
        bottom_air_transfer = (self.bottom_temp - self.air_temp) * 0.01
        self.air_temp += (top_air_transfer + bottom_air_transfer) * dt

        # heat loss
        self.air_temp -= (self.air_temp - self.ambient) * 0.001 * dt

        # update TC
        self.tc.update(dt)

    def set_heat(self, total_output = 1500, bias = 0):
        #The relay stuff is below
        top_fraction = (1 + bias) / 2
        self.top_element.set_output(total_output * top_fraction)
        self.bottom_element.set_output(total_output * (1 - top_fraction))



class PID:
    def __init__(self, kp, ki, kd, output_min=0.0, output_max=1.0, integral_limit = 1000):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.integral_limit = integral_limit

        self.integral = 0.0
        self.previous_error = 0.0

    def update(self, setpoint, measurement, dt):

        error = setpoint - measurement

        self.integral += error * dt
        self.integral = max(-self.integral_limit,min(self.integral_limit, self.integral))

        derivative = (error - self.previous_error) / dt

        output = (self.kp * error + self.ki * self.integral + self.kd * derivative)
        self.previous_error = error

        return max(self.output_min, min(self.output_max, output))


if __name__ == "__main__":

    oven = Oven()
    pid = PID(kp = 0.01, ki = 0.0001, kd = 0.05)

    dt = 1.0
    simulation_time = 1200
    setpoint = 500

    for t in range(simulation_time):
        measured_temp = oven.tc.read()

        power = pid.update(setpoint, measured_temp, dt)
        oven.set_heat(power, 0.5)
        oven.update(dt)

        print(f"{t}s | " f"Actual={oven.air_temp:.1f}F | " f"Measured={measured_temp:.1f}F | "f"Power={power:.2f}")

    # UI with graph for current oven temperature (use qt)
    # Run 10x as fast as normal
    # Collect data like overshoot, tau, etc... see ee380 notes
    # ability to set target in simulation