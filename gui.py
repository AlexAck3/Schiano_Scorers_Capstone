import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer

TESTING_TEMP_READING = 75   # REPLACE THIS CONSTANT WITH THE TC READING

# ------ BUTTON INCREMENTS (+/-) -------
TEMP_TGT_INCREMENT = 5      # F
TIMER_INCREMENT = 1         # Minutes
COIL_RATIO_INCREMENT = 5    # %
# --------------------------------------

# ------------- MAXIMUMS ---------------
MAX_TGT_TEMP = 900          # F
MAX_TIMER_AMT = 180         # Minutes
# --------------------------------------


class PizzaOvenGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pizza Oven Controls")
        self.setFixedSize(500, 800)     # NOTE: Set the the size to the display size

        # Control Variable
        self.temp_target = 500          # F
        self.temp_reading = TESTING_TEMP_READING         # F (Reaplace with TC Reading)
        self.timer_preset = 30          # Start with 30 minutes
        self.timer_remaining = self.timer_preset * 60  # seconds
        self.top_coil = 50              # Percentages
        self.bottom_coil = 50

        # Initalize the timer
        self.countdown = QTimer(self)
        self.countdown.setInterval(1000)    # Seconds
        self.countdown.timeout.connect(self.tick)

        self.build_ui()
        self.refresh()

    # ---------- UI helpers ----------
    def make_label(self, text): # Used for the entry labels
        lbl = QLabel(text)      # Set the text immediately when initalizing a label
        lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl

    def make_entry(self):       # Uneditable Entries for displays
        entry = QLineEdit()
        entry.setReadOnly(True) 
        entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        entry.setFont(QFont("Arial", 20))
        entry.setFixedHeight(50)
        return entry

    def make_step_button(self, text, callback):     # Incremental Buttons
        btn = QPushButton(text)
        btn.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        btn.setFixedSize(60, 50)
        btn.clicked.connect(callback)
        return btn

    # Make each control section that requires incrementation (+/-)
    def make_control(self, title, minus_cb, plus_cb):
        """Label on top, then [-] [entry] [+] below it. Returns (layout, entry, minus, plus)."""
        box = QVBoxLayout()     # Create a box to put this all into
        box.setSpacing(6)
        box.addWidget(self.make_label(title))

        row = QHBoxLayout()
        minus_bt = self.make_step_button("-", minus_cb)
        plus_bt = self.make_step_button("+", plus_cb)
        entry = self.make_entry()
        row.addWidget(minus_bt)     # Configure the row
        row.addWidget(entry)
        row.addWidget(plus_bt)
        box.addLayout(row)          # Add the row to the Layout
        return box, entry, minus_bt, plus_bt

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
        box, self.target_entry, _, _ = self.make_control(       # The minus and plus button pointers are not needed
            "Temperature Target",
            lambda: self.change_temp_target(-TEMP_TGT_INCREMENT),
            lambda: self.change_temp_target(TEMP_TGT_INCREMENT),
        )
        layout.addLayout(box)

        # 3) Temperature reading (no buttons, no user input needed) - Direct TC Feedback
        layout.addWidget(self.make_label("Temperature Reading"))
        self.reading_entry = self.make_entry()
        layout.addWidget(self.reading_entry)

        # 4) Timer - Allows user to modify how much time to cook pizza
        box, self.timer_entry, self.timer_minus, self.timer_plus = self.make_control(
            "Timer",
            lambda: self.change_timer(-TIMER_INCREMENT),
            lambda: self.change_timer(TIMER_INCREMENT),
        )
        layout.addLayout(box)

        # 6) Coils (linked)
        box, self.top_entry, _, _ = self.make_control(      # The minus and plus button pointers are not needed
            "Top Coil",
            lambda: self.change_coils(-COIL_RATIO_INCREMENT),
            lambda: self.change_coils(COIL_RATIO_INCREMENT),
        )
        layout.addLayout(box)

        box, self.bottom_entry, _, _ = self.make_control(
            "Bottom Coil",
            # Flipped change_coils functions, because adding the bottom should subtract the top ratio and vice versa
            lambda: self.change_coils(COIL_RATIO_INCREMENT),    # bottom down -> top up
            lambda: self.change_coils(-COIL_RATIO_INCREMENT),   # bottom up -> top down
        )
        layout.addLayout(box)

        layout.addStretch()

        # Start button - Starts the cooking
        # NOTE: May want to add a preheat button?
        self.start_btn = QPushButton("START")
        self.start_btn.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.start_btn.setFixedHeight(60)
        self.start_btn.setStyleSheet(
            "QPushButton { color: white; background-color: #27ae60; border-radius: 8px; }"
            "QPushButton:disabled { background-color: #7f8c8d; }"
        )
        self.start_btn.clicked.connect(self.start_timer)    # This function should start heating too
        layout.addWidget(self.start_btn)

        # 5) Stop button - LARGE for safety
        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setFont(QFont("Arial", 36, QFont.Weight.Bold))
        self.stop_btn.setFixedHeight(120)
        self.stop_btn.setStyleSheet(
            "QPushButton { color: white; background-color: #c0392b; border-radius: 10px; }"
            "QPushButton:pressed { background-color: #922b21; }"
        )
        self.stop_btn.clicked.connect(self.stop_timer)      # This function should CUT OFF HEATING
        layout.addWidget(self.stop_btn)

        self.setLayout(layout)

    # Refresh all labels with updated info when necessary
    def refresh(self):
        self.target_entry.setText(f"{self.temp_target} °F")
        self.reading_entry.setText(f"{self.temp_reading} °F")
        mins, secs = divmod(self.timer_remaining, 60)
        self.timer_entry.setText(f"{mins:02d}:{secs:02d}")
        self.top_entry.setText(f"{self.top_coil}%")
        self.bottom_entry.setText(f"{self.bottom_coil}%")

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
            self.set_timer_buttons_enabled(False)       # Disable the timer buttons

    # NOTE: This function will need to be implemented into a larger function that cuts off heat
    def stop_timer(self):
        self.countdown.stop()
        self.timer_remaining = self.timer_preset * 60   # Reset the timer to its set amt
        self.set_timer_buttons_enabled(True)            # Re-enable the timer buttons
        self.refresh()

    def tick(self):
        self.timer_remaining -= 1
        if self.timer_remaining <= 0:
            self.timer_remaining = 0
            self.countdown.stop()
            # NOTE: Replace this with the general stop function that cuts off heating
            self.stop_timer()       # Resets the start button
        self.refresh()

    # Enable/Disable the timer buttons when running
    def set_timer_buttons_enabled(self, enabled):
        self.timer_minus.setEnabled(enabled)
        self.timer_plus.setEnabled(enabled)
        self.start_btn.setEnabled(enabled)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PizzaOvenGUI()
    window.show()
    sys.exit(app.exec())