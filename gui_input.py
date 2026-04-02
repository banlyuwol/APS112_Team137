# gui_input.py
# ------------
# Tkinter GUI for circadian LED setup.
# Collects date/time, then starts LED loop at safe brightness.
# Includes option to turn LEDs off.

import tkinter as tk
from datetime import datetime, date
import threading

from sun_calc import calculate_sun_times
import led_controller

# Canada average
CANADA_LAT = 56.1304
CANADA_LON = -106.3468
TZ_STD = -6
TZ_DST = -5

# GUI-safe brightness factor (reduce intensity)
GUI_BRIGHTNESS_CAP = 0.3  # 0.0–1.0

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Circadian LED Setup")

        # Inputs
        now = datetime.now()

        tk.Label(self, text="Date (YYYY-MM-DD)").pack()
        self.date_entry = tk.Entry(self)
        self.date_entry.insert(0, now.strftime("%Y-%m-%d"))
        self.date_entry.pack()

        tk.Label(self, text="Time (HH:MM)").pack()
        self.time_entry = tk.Entry(self)
        self.time_entry.insert(0, now.strftime("%H:%M"))
        self.time_entry.pack()

        tk.Button(self, text="Start LEDs", command=self.start_led).pack(pady=10)
        tk.Button(self, text="Turn Off LEDs", command=self.turn_off_leds).pack(pady=5)

        self.led_thread = None

    def start_led(self):
        try:
            # Parse input
            d = date.fromisoformat(self.date_entry.get())
            t = datetime.strptime(self.time_entry.get(), "%H:%M").time()

            # Calculate sun times
            st = calculate_sun_times(
                d,
                CANADA_LAT,
                CANADA_LON,
                TZ_STD,
                TZ_DST,
                True
            )

            # Stop previous loop if running
            if self.led_thread and self.led_thread.is_alive():
                led_controller.leds_off()

            # Start LED loop in background
            self.led_thread = threading.Thread(
                target=led_controller.run_loop,
                kwargs={
                    "sun_times": {
                        "sunrise_frac": st["sunrise_frac"],
                        "noon_frac": st["noon_frac"],
                        "sunset_frac": st["sunset_frac"],
                    },
                    "poll_interval": 30,
                    "verbose": False,
                    "gui_brightness_cap": GUI_BRIGHTNESS_CAP  # pass GUI dimming
                },
                daemon=True
            )
            self.led_thread.start()

        except Exception as e:
            print("Error:", e)

    def turn_off_leds(self):
        led_controller.leds_off()
        print("[GUI] LEDs turned off.")


if __name__ == "__main__":
    app = App()
    app.mainloop()
