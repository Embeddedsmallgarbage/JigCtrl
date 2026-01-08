import tkinter as tk
from tkinter import ttk
import datetime
import time
import threading

class TestControlFrame(ttk.Frame):
    def __init__(self, master=None, settings_source=None, log_callback=None):
        super().__init__(master)
        self.settings_source = settings_source
        self.log = log_callback if log_callback else print
        self.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        self.timer_id = None
        self.remaining_seconds = 0
        self.remaining_counts = 0
        self.is_running = False
        self.is_paused = False
        self.stop_requested = False
        self.pause_requested = False
        self.current_test_thread = None
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
            self.resume_test()
        else:
            # New Start Logic
            if not self.settings_source:
                self.log("Error: Settings source not available", "ERR")
                return

            settings = self.settings_source.get_current_state()
            mode = settings.get('test_mode')
            target = settings.get('target_value', 0)
            
            # Initialize remaining values
            if mode == 'time':
                unit = settings.get('time_unit', 'Seconds')
                if unit == 'Minutes':
                    self.remaining_seconds = target * 60
                elif unit == 'Hours':
                    self.remaining_seconds = target * 3600
                else:
                    self.remaining_seconds = target
                
                # Initial display for time
                m, s = divmod(self.remaining_seconds, 60)
                h, m = divmod(m, 60)
                self.lbl_remaining.config(text=f"Remaining: {h:02d}:{m:02d}:{s:02d}")
            else:
                self.remaining_counts = target
                self.lbl_remaining.config(text=f"Remaining: {self.remaining_counts} (Counts)")
            
            # Reset Flags
            self.is_running = True
            self.is_paused = False
            self.stop_requested = False
            self.pause_requested = False
            
            # Start Thread
            self.current_test_thread = threading.Thread(target=self.run_test_cycle, daemon=True)
            self.current_test_thread.start()
            
            if mode == 'time':
                self.run_timer()
            
        self.update_ui_state("TESTING")
        self.log("Test Started", "TEST")

    def update_ui_state(self, state):
        if state == "TESTING":
            self.lbl_status.config(text="Current State: TESTING", foreground="green")
            self.btn_start.config(state=tk.DISABLED)
            self.btn_pause.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.NORMAL)
        elif state == "PAUSED":
            self.lbl_status.config(text="Current State: PAUSED", foreground="orange")
            self.btn_start.config(state=tk.NORMAL, text="Resume")
            self.btn_pause.config(state=tk.DISABLED)
        elif state == "STANDBY":
            self.lbl_status.config(text="Current State: STANDBY", foreground="gray")
            self.btn_start.config(state=tk.NORMAL, text="Start Test")
            self.btn_pause.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.DISABLED)
            self.lbl_remaining.config(text="Remaining: --")

    def run_timer(self):
        if not self.is_running or self.is_paused:
            return

        if self.remaining_seconds >= 0:
            m, s = divmod(self.remaining_seconds, 60)
            h, m = divmod(m, 60)
            self.lbl_remaining.config(text=f"Remaining: {h:02d}:{m:02d}:{s:02d}")
            
            if self.remaining_seconds == 0:
                self.stop_requested = True # Signal thread to stop after cycle
                return

            self.remaining_seconds -= 1
            self.timer_id = self.after(1000, self.run_timer)

    def run_test_cycle(self):
        settings = self.settings_source.get_current_state()
        relay_conn = self.settings_source.get_serial_connection("Relay (Solenoid)")
        
        press_duration = settings.get('press_duration', 100) / 1000.0
        interval = settings.get('press_interval', 500) / 1000.0
        mode = settings.get('test_mode')

        # Hex Commands
        CMD_OPEN = bytes.fromhex("A0 01 00 A2")
        CMD_CLOSE = bytes.fromhex("A0 01 00 A1")

        while self.is_running:
            if self.stop_requested:
                break
            
            if self.pause_requested:
                self.is_paused = True
                while self.pause_requested: # Wait until resumed
                    time.sleep(0.1)
                    if self.stop_requested:
                        break
                self.is_paused = False
                if self.stop_requested:
                    break

            # --- Start Cycle ---
            try:
                if relay_conn and relay_conn.is_open:
                    relay_conn.write(CMD_OPEN)
                    self.log("Relay OPEN", "REL")
            except Exception as e:
                self.log(f"Error writing to Relay: {e}", "ERR")

            time.sleep(press_duration)

            try:
                if relay_conn and relay_conn.is_open:
                    relay_conn.write(CMD_CLOSE)
                    self.log("Relay CLOSE", "REL")
            except Exception as e:
                self.log(f"Error writing to Relay: {e}", "ERR")
            
            time.sleep(interval)
            # --- End Cycle ---

            # Update Counts if applicable
            if mode == 'count':
                self.remaining_counts -= 1
                # Update UI from thread safely? Tkinter is not thread safe, but config often works.
                # Better to use after/event, but for simple label update:
                self.lbl_remaining.after(0, lambda: self.lbl_remaining.config(text=f"Remaining: {self.remaining_counts} (Counts)"))
                
                if self.remaining_counts <= 0:
                    break
        
        # Cleanup after loop finishes
        self.is_running = False
        self.lbl_remaining.after(0, self.finish_test)

    def finish_test(self):
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
        self.update_ui_state("STANDBY")
        self.log("Test Finished/Stopped", "TEST")

    def pause_test(self):
        self.pause_requested = True
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
        self.update_ui_state("PAUSED")
        self.log("Test Pause Requested (waiting for cycle to finish)", "TEST")

    def resume_test(self):
        self.pause_requested = False # Unblock thread
        settings = self.settings_source.get_current_state()
        if settings.get('test_mode') == 'time':
            self.run_timer()
        self.update_ui_state("TESTING")
        self.log("Test Resumed", "TEST")

    def stop_test(self):
        self.stop_requested = True
        self.pause_requested = False # Unblock if paused so it can exit
        self.log("Test Stop Requested (waiting for cycle to finish)", "TEST")
