class HeatingElement:
    def __init__(self, max_power_watts):
        self.max_power = max_power_watts
        self.output = 0.0   #simulates the duty cycle

    def set_output(self, output):
        self.output = max(0.0, min(1.0, output))

    @property
    def power(self):
        return self.max_power * self.output #returns the max power times the functional duty cycle