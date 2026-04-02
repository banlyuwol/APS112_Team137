"""
gui_input.py
------------
Tkinter GUI that launches automatically when the Pi boots / user connects.
Collects: city (or custom lat/lon), date, time, number of LEDs.
Writes settings to config.json and launches the LED controller loop.
"""
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

        tk.Button(self, text="Start", command=self.start_led).pack(pady=10)

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

            # Start LED loop in background
            threading.Thread(
                target=led_controller.run_loop,
                args=({
                    "sunrise_frac": st["sunrise_frac"],
                    "noon_frac": st["noon_frac"],
                    "sunset_frac": st["sunset_frac"],
                }, 30),
                daemon=True
            ).start()

        except Exception as e:
            print("Error:", e)


if __name__ == "__main__":
    app = App()
    app.mainloop()
