import tkinter as tk
from tkinter import ttk
import datetime

class TestControlFrame(ttk.Frame):
    def __init__(self, master=None, settings_source=None):
        super().__init__(master)
        self.settings_source = settings_source
        self.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        self.timer_id = None
        self.remaining_seconds = 0
        self.create_widgets()

    def create_widgets(self):
        # Status Display
        status_frame = ttk.LabelFrame(self, text="Status Monitor", padding=20)
        status_frame.pack(fill=tk.X, pady=10)

        self.lbl_status = ttk.Label(status_frame, text="Current State: STANDBY", font=("Cambria", 14, "bold"), foreground="gray")
        self.lbl_status.pack(pady=5)

        self.lbl_remaining = ttk.Label(status_frame, text="Remaining: --", font=("Cambria", 12))
        self.lbl_remaining.pack(pady=5)

        # Control Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)

        self.btn_start = ttk.Button(btn_frame, text="Start Test", command=self.start_test)
        self.btn_pause = ttk.Button(btn_frame, text="Pause", command=self.pause_test, state=tk.DISABLED)
        self.btn_stop = ttk.Button(btn_frame, text="Stop", command=self.stop_test, state=tk.DISABLED)

        self.btn_start.pack(side=tk.LEFT, padx=10)
        self.btn_pause.pack(side=tk.LEFT, padx=10)
        self.btn_stop.pack(side=tk.LEFT, padx=10)

    def start_test(self):
        if self.btn_start['text'] == "Resume":
            # Resume logic
            self.run_timer()
        else:
            # New Start Logic
            if self.settings_source:
                settings = self.settings_source.get_current_state()
                mode = settings.get('test_mode')
                target = settings.get('target_value', 0)
                
                if mode == 'time':
                    unit = settings.get('time_unit', 'Seconds')
                    if unit == 'Minutes':
                        self.remaining_seconds = target * 60
                    elif unit == 'Hours':
                        self.remaining_seconds = target * 3600
                    else:
                        self.remaining_seconds = target
                    
                    self.run_timer()
                else:
                    self.lbl_remaining.config(text=f"Remaining: {target} (Counts)")
            
        self.lbl_status.config(text="Current State: TESTING", foreground="green")
        self.btn_start.config(state=tk.DISABLED)
        self.btn_pause.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.NORMAL)
        print("Test Started")

    def run_timer(self):
        if self.remaining_seconds >= 0:
            m, s = divmod(self.remaining_seconds, 60)
            h, m = divmod(m, 60)
            self.lbl_remaining.config(text=f"Remaining: {h:02d}:{m:02d}:{s:02d}")
            
            if self.remaining_seconds == 0:
                self.stop_test()
                return

            self.remaining_seconds -= 1
            self.timer_id = self.after(1000, self.run_timer)

    def pause_test(self):
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
            
        self.lbl_status.config(text="Current State: PAUSED", foreground="orange")
        self.btn_start.config(state=tk.NORMAL, text="Resume")
        self.btn_pause.config(state=tk.DISABLED)
        print("Test Paused")

    def stop_test(self):
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
            
        self.lbl_status.config(text="Current State: STANDBY", foreground="gray")
        self.btn_start.config(state=tk.NORMAL, text="Start Test")
        self.btn_pause.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        self.lbl_remaining.config(text="Remaining: --")
        print("Test Stopped")
