import sys
import random
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal

from PyQt6.QtGui import QFont, QPalette, QColor   # add QPalette, QColor to the existing import

def apply_light_theme(app):
    app.setStyle("Fusion")   # Fusion respects custom palettes on every platform
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor("white"))
    p.setColor(QPalette.ColorRole.WindowText, QColor("black"))
    p.setColor(QPalette.ColorRole.Base, QColor("white"))        # entry backgrounds
    p.setColor(QPalette.ColorRole.Text, QColor("black"))        # entry text
    p.setColor(QPalette.ColorRole.Button, QColor("#f0f0f0"))
    p.setColor(QPalette.ColorRole.ButtonText, QColor("black"))
    app.setPalette(p)

# =====================================================================
# LAPTOP TEST VERSION - no gpiozero / board / smbus2 / mlx90614 needed.
#   Keyboard replaces the hardware:
#     Up / Down       -> up_button / down_button (move selection)
#     Left / Right    -> encoder counter-clockwise / clockwise
#     Enter / Space   -> encoder push button
#     Esc             -> quit
#   Sensor readings are simulated (random walk) instead of read from SPI/I2C.
# =====================================================================

# ------ ENCODER INCREMENTS (per detent) -------
TEMP_TGT_INCREMENT = 5      # F
TIMER_INCREMENT = 1         # Minutes
COIL_RATIO_INCREMENT = 5    # %
# ----------------------------------------------

# ------------- MAXIMUMS ---------------
MAX_TGT_TEMP = 900          # F
MAX_TIMER_AMT = 180         # Minutes
# --------------------------------------

# ------------- SENSOR CONFIG -------------
# MAX31856 chip-select pins (BCM GPIO numbers). All three amps share the SPI0 bus
# (SCLK=GPIO11, MISO=GPIO9, MOSI=GPIO10); only CS is unique per amp.
# Pins already used elsewhere: 16/20/21 (buttons), 5/6 (encoder), 19/26 (PWM/coil select),
# 2/3 (I2C), 7-11 (SPI0).
TC_CS_PINS = {
    "oven": 8,      # CE0   -> "Temperature Reading"
    "top": 25,      # Physical pin 22 -> "Top Coil Temp"
    "bottom": 24,   # Physical pin 18 -> "Bottom Coil Temp"
}
IR_I2C_ADDR = 0x5A              # Check with: i2cdetect -y 1
SENSOR_POLL_MS = 500            # Delay between sensor sweeps
# -----------------------------------------

# ------------- SELECTION STYLES -------------
ENTRY_STYLE = "QLineEdit { border: 2px solid #999999; border-radius: 4px; }"
ENTRY_STYLE_SELECTED = (
    "QLineEdit { border: 5px solid #2980b9; border-radius: 4px; background-color: #eaf4fc; }"
)
DISPLAY_STYLE = "QLineEdit { border: none; background: transparent; }"
START_STYLE = (
    "QPushButton { color: white; background-color: #27ae60; border-radius: 8px; border: 5px solid #27ae60; }"
    "QPushButton:disabled { background-color: #7f8c8d; border: 5px solid #7f8c8d; }"
)
START_STYLE_SELECTED = (
    "QPushButton { color: white; background-color: #27ae60; border-radius: 8px; border: 5px solid #2980b9; }"
    "QPushButton:disabled { background-color: #7f8c8d; border: 5px solid #2980b9; }"
)
STOP_STYLE = (
    "QPushButton { color: white; background-color: #c0392b; border-radius: 10px; border: 5px solid #c0392b; }"
    "QPushButton:pressed { background-color: #922b21; }"
)
STOP_STYLE_SELECTED = (
    "QPushButton { color: white; background-color: #c0392b; border-radius: 10px; border: 5px solid #2980b9; }"
    "QPushButton:pressed { background-color: #922b21; }"
)
# --------------------------------------------

# Indexes into the selection order (see PizzaOvenGUI.build_ui)
SEL_TEMP, SEL_TIMER, SEL_COIL, SEL_START, SEL_STOP = range(5)


def c_to_f(c):
    return c * 9 / 5 + 32


class SensorWorker(QThread):
    """SIMULATED sensors for laptop testing. Same signal/dict format as the real one:
        {"oven": f, "top": f, "bottom": f, "stone": f}   (None = no reading)
    Values random-walk upward from room temp so you can see the fields update.
    The pizza stone reads None for the first few sweeps to test the "-- F" display.
    """
    sig_readings = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._vals = {"oven": 75.0, "top": 75.0, "bottom": 75.0, "stone": 75.0}

    def stop(self):
        self._running = False

    def run(self):
        sweep = 0
        while self._running:
            for name in self._vals:
                self._vals[name] = max(60.0, min(900.0, self._vals[name] + random.uniform(-3, 12)))
            data = dict(self._vals)
            if sweep < 4:
                data["stone"] = None
            sweep += 1
            self.sig_readings.emit(data)
            self.msleep(SENSOR_POLL_MS)


class PizzaOvenGUI(QWidget):
    # On the Pi, hardware callbacks fire on a background thread, so the real GUI routes
    # them through these signals. Kept here so the test file behaves identically.
    sig_up = pyqtSignal()
    sig_down = pyqtSignal()
    sig_select = pyqtSignal()
    sig_rotate = pyqtSignal(int)    # +1 = clockwise, -1 = counter-clockwise

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pizza Oven Controls (LAPTOP TEST)")
        self.setFixedSize(500, 800)     # NOTE: Set the the size to the display size

        # Control Variable
        self.temp_target = 500          # F
        self.temp_reading = None        # F - oven TC (None until first reading)
        self.top_coil_temp = None       # F - top coil TC
        self.bottom_coil_temp = None    # F - bottom coil TC
        self.stone_temp = None          # F - IR sensor (pizza stone)
        self.timer_preset = 30          # Start with 30 minutes
        self.timer_remaining = self.timer_preset * 60  # seconds
        self.top_coil = 50              # Percentages
        self.bottom_coil = 50
        self.sel_index = 0              # Which item is currently highlighted

        # Initalize the timer
        self.countdown = QTimer(self)
        self.countdown.setInterval(1000)    # Seconds
        self.countdown.timeout.connect(self.tick)

        self.build_ui()
        self.setup_hardware()
        self.refresh()
        self.update_selection()

        # Start reading sensors
        self.sensor_worker = SensorWorker(self)
        self.sensor_worker.sig_readings.connect(self.on_sensor_readings)
        self.sensor_worker.start()

    # ---------- UI helpers ----------
    def make_label(self, text): # Used for the entry labels
        lbl = QLabel(text)      # Set the text immediately when initalizing a label
        lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl

    def make_entry(self):       # Uneditable Entries for displays
        entry = QLineEdit()
        entry.setReadOnly(True)
        entry.setFocusPolicy(Qt.FocusPolicy.NoFocus)    # Selection is driven by the hardware buttons
        entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        entry.setFont(QFont("Arial", 20))
        entry.setFixedHeight(50)
        entry.setStyleSheet(ENTRY_STYLE)
        return entry

    # Make each control section: label on top, entry below it. Returns (layout, entry).
    def make_control(self, title):
        box = QVBoxLayout()     # Create a box to put this all into
        box.setSpacing(6)
        box.addWidget(self.make_label(title))
        entry = self.make_entry()
        box.addWidget(entry)
        return box, entry

    # Same as make_control, but for non-selectable display-only values (no border)
    def make_display_control(self, title):
        box, entry = self.make_control(title)
        entry.setCursor(Qt.CursorShape.ArrowCursor)
        entry.setStyleSheet(DISPLAY_STYLE)
        return box, entry

    def build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 20, 25, 25)
        layout.setSpacing(18)

        # 1) Title - Placed at the top of the page, purely decrotive
        title = QLabel("PIZZA OVEN CONTROLS")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 2) Temperature target - Allows user to modify the PID temperature target
        box, self.target_entry = self.make_control("Temperature Target")
        layout.addLayout(box)

        # 3) Temperature reading (oven TC) and pizza stone (IR) - not selectable, side by side
        row = QHBoxLayout()
        row.setSpacing(12)
        box, self.reading_entry = self.make_display_control("Temperature Reading")
        row.addLayout(box)
        box, self.stone_entry = self.make_display_control("Pizza Stone")
        row.addLayout(box)
        layout.addLayout(row)

        # 4) Timer - Allows user to modify how much time to cook pizza
        box, self.timer_entry = self.make_control("Timer")
        layout.addLayout(box)

        # 5) Coils (linked) - Only the top coil % is selectable; the bottom coil follows (100 - top)
        #    Each row: coil power % on the left, that coil's TC temperature on the right
        row = QHBoxLayout()
        row.setSpacing(12)
        box, self.top_entry = self.make_control("Top Coil %")
        row.addLayout(box)
        box, self.top_temp_entry = self.make_display_control("Top Coil Temp")
        row.addLayout(box)
        layout.addLayout(row)

        row = QHBoxLayout()
        row.setSpacing(12)
        box, self.bottom_entry = self.make_display_control("Bottom Coil %")
        row.addLayout(box)
        box, self.bottom_temp_entry = self.make_display_control("Bottom Coil Temp")
        row.addLayout(box)
        layout.addLayout(row)

        layout.addStretch()

        # Start button - Starts the cooking
        # NOTE: May want to add a preheat button?
        self.start_btn = QPushButton("START")
        self.start_btn.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.start_btn.setFixedHeight(60)
        self.start_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.start_btn.setStyleSheet(START_STYLE)
        self.start_btn.clicked.connect(self.start_timer)    # This function should start heating too
        layout.addWidget(self.start_btn)

        # 6) Stop button - LARGE for safety
        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setFont(QFont("Arial", 36, QFont.Weight.Bold))
        self.stop_btn.setFixedHeight(120)
        self.stop_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.stop_btn.setStyleSheet(STOP_STYLE)
        self.stop_btn.clicked.connect(self.stop_timer)      # This function should CUT OFF HEATING
        layout.addWidget(self.stop_btn)

        self.setLayout(layout)

        # Selection order (matches the SEL_* indexes). Each entry: (object, normal style, selected style)
        self.selectables = [
            (self.target_entry, ENTRY_STYLE, ENTRY_STYLE_SELECTED),     # SEL_TEMP
            (self.timer_entry, ENTRY_STYLE, ENTRY_STYLE_SELECTED),      # SEL_TIMER
            (self.top_entry, ENTRY_STYLE, ENTRY_STYLE_SELECTED),        # SEL_COIL
            (self.start_btn, START_STYLE, START_STYLE_SELECTED),        # SEL_START
            (self.stop_btn, STOP_STYLE, STOP_STYLE_SELECTED),           # SEL_STOP
        ]

    # ---------- Hardware ----------
    def setup_hardware(self):
        # Signals -> GUI-thread handlers (same as the Pi version)
        self.sig_up.connect(self.select_previous)
        self.sig_down.connect(self.select_next)
        self.sig_select.connect(self.activate_selected)
        self.sig_rotate.connect(self.on_rotate)

    # Keyboard stands in for the buttons and rotary encoder
    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Up:
            self.sig_up.emit()
        elif key == Qt.Key.Key_Down:
            self.sig_down.emit()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.sig_select.emit()
        elif key == Qt.Key.Key_Right:
            self.sig_rotate.emit(1)
        elif key == Qt.Key.Key_Left:
            self.sig_rotate.emit(-1)
        elif key == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def on_sensor_readings(self, data):
        # Runs on the GUI thread (signal from SensorWorker)
        self.temp_reading = data.get("oven")
        self.top_coil_temp = data.get("top")
        self.bottom_coil_temp = data.get("bottom")
        self.stone_temp = data.get("stone")
        self.refresh()

    def closeEvent(self, event):
        self.sensor_worker.stop()
        self.sensor_worker.wait(2000)
        super().closeEvent(event)

    # ---------- Selection ----------
    def select_previous(self):
        # "Up" moves toward the top of the screen; wraps to the last item
        if self.sel_index > 0:
            self.sel_index -= 1
            self.update_selection()
        else:
            self.sel_index = len(self.selectables) - 1
            self.update_selection()

    def select_next(self):
        # "Down" moves toward the bottom of the screen; wraps to the first item
        if self.sel_index < len(self.selectables) - 1:
            self.sel_index += 1
            self.update_selection()
        else:
            self.sel_index = 0
            self.update_selection()

    def update_selection(self):
        for i, (widget, normal, selected) in enumerate(self.selectables):
            widget.setStyleSheet(selected if i == self.sel_index else normal)

    def on_rotate(self, direction):
        # Turning the encoder adjusts whichever entry is highlighted
        if self.sel_index == SEL_TEMP:
            self.change_temp_target(direction * TEMP_TGT_INCREMENT)
        elif self.sel_index == SEL_TIMER:
            self.change_timer(direction * TIMER_INCREMENT)
        elif self.sel_index == SEL_COIL:
            self.change_coils(direction * COIL_RATIO_INCREMENT)
        # START / STOP highlighted: rotation does nothing

    def activate_selected(self):
        # Pressing the encoder only does something when START or STOP is highlighted
        if self.sel_index == SEL_START:
            self.start_timer()
        elif self.sel_index == SEL_STOP:
            self.stop_timer()

    # Format a temperature (F) for display; "--" if there's no valid reading yet
    @staticmethod
    def fmt_temp(value):
        return "-- °F" if value is None else f"{value:.0f} °F"

    # Refresh all labels with updated info when necessary
    def refresh(self):
        self.target_entry.setText(f"{self.temp_target} °F")
        self.reading_entry.setText(self.fmt_temp(self.temp_reading))
        self.stone_entry.setText(self.fmt_temp(self.stone_temp))
        mins, secs = divmod(self.timer_remaining, 60)
        self.timer_entry.setText(f"{mins:02d}:{secs:02d}")
        self.top_entry.setText(f"{self.top_coil}%")
        self.bottom_entry.setText(f"{self.bottom_coil}%")
        self.top_temp_entry.setText(self.fmt_temp(self.top_coil_temp))
        self.bottom_temp_entry.setText(self.fmt_temp(self.bottom_coil_temp))

    # ---------- Logic ----------
    def change_temp_target(self, delta):
        # Target temperature must be between 0 and MAX_TGT_TEMP
        self.temp_target = max(0, min(MAX_TGT_TEMP, self.temp_target + delta))
        self.refresh()

    def change_timer(self, delta):
        if self.countdown.isActive():
            return
        # Timer Count must be between 0 and MAX_TIMER_AMT
        self.timer_preset = max(0, min(MAX_TIMER_AMT, self.timer_preset + delta))
        self.timer_remaining = self.timer_preset * 60
        self.refresh()

    def change_coils(self, delta_top):
        new_top = self.top_coil + delta_top
        # Ensure the coil percentages still equal 100%
        if 0 <= new_top <= 100:
            self.top_coil = new_top
            self.bottom_coil = 100 - new_top
        self.refresh()

    # NOTE: This function will need to be implemented into a larger function that starts the heat
    # NOTE: Or not, if we add a preheat button
    def start_timer(self):
        # Ensure the timer is set higher than zero and is not currently running
        if self.timer_remaining > 0 and not self.countdown.isActive():
            self.countdown.start()
            self.set_timer_buttons_enabled(False)       # Disable the timer/start controls

    # NOTE: This function will need to be implemented into a larger function that cuts off heat
    def stop_timer(self):
        self.countdown.stop()
        self.timer_remaining = self.timer_preset * 60   # Reset the timer to its set amt
        self.set_timer_buttons_enabled(True)            # Re-enable the timer/start controls
        self.refresh()

    def tick(self):
        self.timer_remaining -= 1
        if self.timer_remaining <= 0:
            self.timer_remaining = 0
            self.countdown.stop()
            # NOTE: Replace this with the general stop function that cuts off heating
            self.stop_timer()       # Resets the start button
        self.refresh()

    # Enable/Disable the start button when running (timer changes are blocked in change_timer)
    def set_timer_buttons_enabled(self, enabled):
        self.start_btn.setEnabled(enabled)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PizzaOvenGUI()
    apply_light_theme(app)
    window.show()          # Windowed for laptop testing
    sys.exit(app.exec())
