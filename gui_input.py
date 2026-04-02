"""
gui_input.py
------------
Tkinter GUI that launches automatically when the Pi boots / user connects.
Collects: city (or custom lat/lon), date, time, number of LEDs.
Writes settings to config.json and launches the LED controller loop.
"""

import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime

from sun_calc import calculate_sun_times, CANADIAN_CITIES
import led_controller


CONFIG_FILE = "/home/pi/circadian_led/config.json"


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def save_config(data: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_config() -> dict:
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# ─────────────────────────────────────────────────────────────
# MAIN GUI CLASS
# ─────────────────────────────────────────────────────────────
class CircadianApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("🌅  Circadian LED Controller")
        self.resizable(False, False)
        self.configure(bg="#1a1a2e")

        self._controller_thread = None
        self._stop_event = threading.Event()

        self._build_styles()
        self._build_ui()
        self._load_saved_config()

    # ── Styles ────────────────────────────────────────────────
    def _build_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        bg   = "#1a1a2e"
        card = "#16213e"
        acc  = "#e94560"
        fg   = "#eaeaea"
        sel  = "#0f3460"

        style.configure("TFrame",       background=bg)
        style.configure("Card.TFrame",  background=card)
        style.configure("TLabel",       background=bg,   foreground=fg,
                        font=("Helvetica", 11))
        style.configure("Card.TLabel",  background=card, foreground=fg,
                        font=("Helvetica", 11))
        style.configure("Head.TLabel",  background=bg,   foreground=acc,
                        font=("Helvetica", 20, "bold"))
        style.configure("Sub.TLabel",   background=bg,   foreground="#aaa",
                        font=("Helvetica", 9))
        style.configure("TEntry",       fieldbackground=sel, foreground=fg,
                        insertcolor=fg)
        style.configure("TCombobox",    fieldbackground=sel, foreground=fg,
                        selectbackground=sel)
        style.configure("TButton",      background=acc,  foreground="#fff",
                        font=("Helvetica", 11, "bold"), padding=8)
        style.map("TButton",
                  background=[("active", "#c73652")])
        style.configure("Stop.TButton", background="#555", foreground="#fff",
                        font=("Helvetica", 11, "bold"), padding=8)
        style.map("Stop.TButton",
                  background=[("active", "#333")])
        style.configure("Info.TLabel",  background=card, foreground="#7ec8e3",
                        font=("Courier", 10))

    # ── UI Layout ─────────────────────────────────────────────
    def _build_ui(self):
        pad = {"padx": 14, "pady": 6}

        # Header
        ttk.Label(self, text="🌅  Circadian LED", style="Head.TLabel"
                  ).grid(row=0, column=0, columnspan=2, pady=(20, 0))
        ttk.Label(self, text="Simulate natural sunlight for your circadian rhythm",
                  style="Sub.TLabel").grid(row=1, column=0, columnspan=2, pady=(0, 16))

        # ── Location card ─────────────────────────────────────
        loc = ttk.LabelFrame(self, text=" 📍 Location ", style="Card.TFrame",
                             padding=10)
        loc.grid(row=2, column=0, columnspan=2, sticky="ew", **pad)
        loc.configure(labelanchor="nw")

        ttk.Label(loc, text="City:", style="Card.TLabel"
                  ).grid(row=0, column=0, sticky="w", pady=4)
        self.city_var = tk.StringVar(value="Toronto")
        city_cb = ttk.Combobox(loc, textvariable=self.city_var,
                               values=list(CANADIAN_CITIES.keys()), width=20,
                               state="readonly")
        city_cb.grid(row=0, column=1, sticky="w", padx=8)
        city_cb.bind("<<ComboboxSelected>>", self._on_city_change)

        # Custom lat/lon (hidden unless "Custom" selected)
        self.lat_frame = ttk.Frame(loc, style="Card.TFrame")
        self.lat_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        ttk.Label(self.lat_frame, text="Latitude:",  style="Card.TLabel"
                  ).grid(row=0, column=0, sticky="w")
        self.lat_var = tk.StringVar(value="43.65")
        ttk.Entry(self.lat_frame, textvariable=self.lat_var, width=10
                  ).grid(row=0, column=1, padx=6)
        ttk.Label(self.lat_frame, text="Longitude:", style="Card.TLabel"
                  ).grid(row=0, column=2, sticky="w", padx=(12, 0))
        self.lon_var = tk.StringVar(value="-79.38")
        ttk.Entry(self.lat_frame, textvariable=self.lon_var, width=10
                  ).grid(row=0, column=3, padx=6)
        self.lat_frame.grid_remove()   # hidden by default

        # DST toggle
        self.dst_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(loc, text="Observe DST (most provinces)",
                        variable=self.dst_var, style="Card.TLabel"
                        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=4)

        # ── Date / Time card ──────────────────────────────────
        dt_card = ttk.LabelFrame(self, text=" 📅 Date & Time ", style="Card.TFrame",
                                 padding=10)
        dt_card.grid(row=3, column=0, columnspan=2, sticky="ew", **pad)

        now = datetime.now()

        ttk.Label(dt_card, text="Date (YYYY-MM-DD):", style="Card.TLabel"
                  ).grid(row=0, column=0, sticky="w")
        self.date_var = tk.StringVar(value=now.strftime("%Y-%m-%d"))
        ttk.Entry(dt_card, textvariable=self.date_var, width=14
                  ).grid(row=0, column=1, padx=8, pady=4)

        ttk.Label(dt_card, text="Current time (HH:MM):", style="Card.TLabel"
                  ).grid(row=1, column=0, sticky="w")
        self.time_var = tk.StringVar(value=now.strftime("%H:%M"))
        ttk.Entry(dt_card, textvariable=self.time_var, width=8
                  ).grid(row=1, column=1, padx=8, pady=4)

        ttk.Button(dt_card, text="Use System Time",
                   command=self._use_system_time
                   ).grid(row=0, column=2, rowspan=2, padx=8)

        # ── LED Hardware card ─────────────────────────────────
        hw_card = ttk.LabelFrame(self, text=" 💡 LED Strip ", style="Card.TFrame",
                                 padding=10)
        hw_card.grid(row=4, column=0, columnspan=2, sticky="ew", **pad)

        ttk.Label(hw_card, text="Number of LEDs:", style="Card.TLabel"
                  ).grid(row=0, column=0, sticky="w")
        self.led_count_var = tk.IntVar(value=60)
        ttk.Entry(hw_card, textvariable=self.led_count_var, width=6
                  ).grid(row=0, column=1, padx=8)

        ttk.Label(hw_card, text="Update interval (sec):", style="Card.TLabel"
                  ).grid(row=1, column=0, sticky="w", pady=4)
        self.interval_var = tk.IntVar(value=30)
        ttk.Entry(hw_card, textvariable=self.interval_var, width=6
                  ).grid(row=1, column=1, padx=8)

        # ── Sun Info display ──────────────────────────────────
        self.info_frame = ttk.LabelFrame(self, text=" ☀️  Calculated Sun Times ",
                                         style="Card.TFrame", padding=10)
        self.info_frame.grid(row=5, column=0, columnspan=2, sticky="ew", **pad)
        self.info_label = ttk.Label(self.info_frame, text="(press Calculate to preview)",
                                    style="Info.TLabel", justify="left")
        self.info_label.grid(sticky="w")

        # ── Buttons ───────────────────────────────────────────
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=14)

        ttk.Button(btn_frame, text="Calculate & Preview",
                   command=self._calculate_preview
                   ).grid(row=0, column=0, padx=6)

        self.start_btn = ttk.Button(btn_frame, text="▶  Start LEDs",
                                    command=self._start_controller)
        self.start_btn.grid(row=0, column=1, padx=6)

        self.stop_btn = ttk.Button(btn_frame, text="■  Stop LEDs",
                                   command=self._stop_controller, style="Stop.TButton")
        self.stop_btn.grid(row=0, column=2, padx=6)
        self.stop_btn.state(["disabled"])

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, style="Sub.TLabel"
                  ).grid(row=7, column=0, columnspan=2, pady=(0, 10))

    # ── Event Handlers ────────────────────────────────────────
    def _on_city_change(self, _event=None):
        city = self.city_var.get()
        if city == "Custom":
            self.lat_frame.grid()
        else:
            self.lat_frame.grid_remove()
            coords = CANADIAN_CITIES.get(city)
            if coords:
                self.lat_var.set(str(coords[0]))
                self.lon_var.set(str(coords[1]))

    def _use_system_time(self):
        now = datetime.now()
        self.date_var.set(now.strftime("%Y-%m-%d"))
        self.time_var.set(now.strftime("%H:%M"))

    def _get_sun_times(self):
    from datetime import date

    CANADA_LAT = 56.1304
    CANADA_LON = -106.3468
    TZ_STD = -6
    TZ_DST = -5

    target = date.fromisoformat(self.date_var.get())

    return calculate_sun_times(
        target,
        CANADA_LAT,
        CANADA_LON,
        TZ_STD,
        TZ_DST,
        True
    )

    def _calculate_preview(self):
        try:
            st = self._get_sun_times()
            self.info_label.config(
                text=(
                    f"  Sunrise  :  {st['sunrise_str']}\n"
                    f"  Solar Noon:  {st['noon_str']}\n"
                    f"  Sunset   :  {st['sunset_str']}\n"
                    f"  Day length:  {st['day_length_h']} hours\n"
                    f"  Timezone  :  {st['timezone']}"
                )
            )
            self.status_var.set("✔  Sun times calculated successfully.")
            return st
        except Exception as e:
            messagebox.showerror("Calculation Error", str(e))
            return None

    def _start_controller(self):
        st = self._calculate_preview()
        if not st:
            return

        # Reconfigure LED strip if count changed
        led_controller.LED_COUNT = self.led_count_var.get()

        self._stop_event.clear()
        self._controller_thread = threading.Thread(
            target=led_controller.run_loop,
            args=(st, self.interval_var.get()),
            daemon=True
        )
        self._controller_thread.start()

        self.start_btn.state(["disabled"])
        self.stop_btn.state(["!disabled"])
        self.status_var.set("▶  LED controller running…")

    def _stop_controller(self):
        self._stop_event.set()
        led_controller.leds_off()
        self.start_btn.state(["!disabled"])
        self.stop_btn.state(["disabled"])
        self.status_var.set("■  LED controller stopped.")

    def _load_saved_config(self):
        cfg = load_config()
        if not cfg:
            return
        self.city_var.set(cfg.get("city", "Toronto"))
        self.lat_var.set(str(cfg.get("lat", 43.65)))
        self.lon_var.set(str(cfg.get("lon", -79.38)))
        self.date_var.set(cfg.get("date", date.today().isoformat()))
        self.led_count_var.set(cfg.get("led_count", 60))
        self.interval_var.set(cfg.get("interval_sec", 30))
        self._on_city_change()


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = CircadianApp()
    app.mainloop()
