import tkinter as tk
from tkinter import ttk
import copy
import serial
import serial.tools.list_ports

class SerialConfigFrame(ttk.LabelFrame):
    def __init__(self, master, title, on_change_callback, port_manager, log_callback):
        super().__init__(master, text=title, padding=10)
        self.on_change = on_change_callback
        self.port_manager = port_manager
        self.log = log_callback
        self.serial_conn = None
        self.create_widgets()

    def create_widgets(self):
        # Grid layout
        self.columnconfigure(1, weight=1)

        # Port Selection
        ttk.Label(self, text="Port:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(self, textvariable=self.port_var, state="readonly")
        self.port_combo.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        self.port_combo.bind("<<ComboboxSelected>>", lambda e: self.on_change())
        self.port_combo.bind('<Button-1>', self.refresh_ports) # Refresh on click

        # Baud Rate
        ttk.Label(self, text="Baud:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.baud_var = tk.IntVar(value=9600)
        self.baud_combo = ttk.Combobox(self, textvariable=self.baud_var, values=[9600, 19200, 38400, 115200], state="readonly")
        self.baud_combo.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        self.baud_combo.bind("<<ComboboxSelected>>", lambda e: self.on_change())

        # Data Bits
        ttk.Label(self, text="Data Bits:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.data_bits_var = tk.IntVar(value=8)
        self.data_bits_combo = ttk.Combobox(self, textvariable=self.data_bits_var, values=[5, 6, 7, 8], state="readonly")
        self.data_bits_combo.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=2)
        self.data_bits_combo.bind("<<ComboboxSelected>>", lambda e: self.on_change())

        # Stop Bits
        ttk.Label(self, text="Stop Bits:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.stop_bits_var = tk.DoubleVar(value=1)
        self.stop_bits_combo = ttk.Combobox(self, textvariable=self.stop_bits_var, values=[1, 1.5, 2], state="readonly")
        self.stop_bits_combo.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=2)
        self.stop_bits_combo.bind("<<ComboboxSelected>>", lambda e: self.on_change())

        # Parity
        ttk.Label(self, text="Parity:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.parity_var = tk.StringVar(value='None')
        self.parity_combo = ttk.Combobox(self, textvariable=self.parity_var, values=['None', 'Even', 'Odd', 'Mark', 'Space'], state="readonly")
        self.parity_combo.grid(row=4, column=1, sticky=tk.EW, padx=5, pady=2)
        self.parity_combo.bind("<<ComboboxSelected>>", lambda e: self.on_change())

        # Open Button
        self.btn_open = ttk.Button(self, text="Open Port", command=self.toggle_port)
        self.btn_open.grid(row=5, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5)
        
        self.is_open = False
        self.refresh_ports()

    def refresh_ports(self, event=None):
        ports = sorted([port.device for port in serial.tools.list_ports.comports()])
        if not ports:
            self.port_combo['values'] = []
            if not self.port_var.get():
                self.port_combo.set('')
        else:
            self.port_combo['values'] = ports
            # If current selection is not in list (and list not empty), maybe clear or keep?
            # Keeping it is better if device was just unplugged momentarily, but usually we want valid ones.
            # If nothing selected, select first? No, leave empty.

    def toggle_port(self):
        if self.is_open:
            # Close Logic
            if self.serial_conn and self.serial_conn.is_open:
                try:
                    self.serial_conn.close()
                except Exception as e:
                    self.log(f"Error closing port: {e}", "ERR")
            self.serial_conn = None
            self.port_manager.release_port(self.port_var.get())
            self.is_open = False
            self.btn_open.config(text="Open Port")
            self.log(f"{self['text']} Port Closed", "SER")
            self.toggle_inputs(True)
        else:
            # Open Logic
            port = self.port_var.get()
            if not port:
                self.log("Error: No port selected", "ERR")
                return
            
            if not self.port_manager.is_port_available(port):
                self.log(f"Error: Port {port} is already in use", "ERR")
                return

            try:
                # Map Parity
                parity_map = {
                    'None': serial.PARITY_NONE,
                    'Even': serial.PARITY_EVEN,
                    'Odd': serial.PARITY_ODD,
                    'Mark': serial.PARITY_MARK,
                    'Space': serial.PARITY_SPACE
                }
                
                self.serial_conn = serial.Serial(
                    port=port,
                    baudrate=self.baud_var.get(),
                    bytesize=self.data_bits_var.get(),
                    stopbits=self.stop_bits_var.get(),
                    parity=parity_map.get(self.parity_var.get(), serial.PARITY_NONE),
                    timeout=0.1
                )
                
                self.port_manager.claim_port(port)
                self.is_open = True
                self.btn_open.config(text="Close Port")
                self.log(f"{self['text']} Port {port} Opened successfully", "SER")
                self.toggle_inputs(False)
            except Exception as e:
                self.log(f"Error opening port {port}: {e}", "ERR")
                self.serial_conn = None

    def toggle_inputs(self, enable):
        state = "readonly" if enable else "disabled"
        self.port_combo.config(state=state)
        self.baud_combo.config(state=state)
        self.data_bits_combo.config(state=state)
        self.stop_bits_combo.config(state=state)
        self.parity_combo.config(state=state)

    def get_settings(self):
        return {
            'port': self.port_var.get(),
            'baud': self.baud_var.get(),
            'data_bits': self.data_bits_var.get(),
            'stop_bits': self.stop_bits_var.get(),
            'parity': self.parity_var.get()
        }

    def get_serial_connection(self):
        return self.serial_conn

class PortManager:
    def __init__(self):
        self.used_ports = set()

    def is_port_available(self, port):
        return port not in self.used_ports

    def claim_port(self, port):
        self.used_ports.add(port)

    def release_port(self, port):
        if port in self.used_ports:
            self.used_ports.remove(port)

class SettingsFrame(ttk.Frame):
    def __init__(self, master=None, log_callback=None):
        super().__init__(master)
        self.log = log_callback if log_callback else print
        self.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.port_manager = PortManager()
        self.vars = {}
        
        self.create_widgets()
        self.save_initial_state()

    def create_widgets(self):
        # Top section: Test Settings
        test_frame = ttk.LabelFrame(self, text="Test Parameters", padding=10)
        test_frame.pack(fill=tk.X, pady=5)

        # Test Mode
        self.vars['test_mode'] = tk.StringVar(value="count")
        ttk.Radiobutton(test_frame, text="By Count (Times)", variable=self.vars['test_mode'], value="count", command=self.on_mode_change).grid(row=0, column=0, padx=10, sticky=tk.W)
        ttk.Radiobutton(test_frame, text="By Time (Duration)", variable=self.vars['test_mode'], value="time", command=self.on_mode_change).grid(row=0, column=1, padx=10, sticky=tk.W)

        # Target Value (Count or Time)
        ttk.Label(test_frame, text="Target Value:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
        self.vars['target_value'] = tk.IntVar(value=100)
        entry_target = ttk.Entry(test_frame, textvariable=self.vars['target_value'])
        entry_target.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        self.vars['target_value'].trace_add("write", lambda *args: self.check_changes())

        # Time Unit (Hidden by default or shown based on mode)
        self.vars['time_unit'] = tk.StringVar(value="Seconds")
        self.unit_combo = ttk.Combobox(test_frame, textvariable=self.vars['time_unit'], values=["Seconds", "Minutes", "Hours"], state="readonly", width=10)
        self.unit_combo.grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.unit_combo.bind("<<ComboboxSelected>>", lambda e: self.check_changes())
        
        # Press Settings
        press_frame = ttk.LabelFrame(self, text="Press Settings", padding=10)
        press_frame.pack(fill=tk.X, pady=5)

        ttk.Label(press_frame, text="Press Duration (ms):").grid(row=0, column=0, padx=5, pady=5)
        self.vars['press_duration'] = tk.IntVar(value=100)
        ttk.Entry(press_frame, textvariable=self.vars['press_duration']).grid(row=0, column=1, padx=5, pady=5)
        self.vars['press_duration'].trace_add("write", lambda *args: self.check_changes())

        ttk.Label(press_frame, text="Interval (ms):").grid(row=0, column=2, padx=5, pady=5)
        self.vars['press_interval'] = tk.IntVar(value=500)
        ttk.Entry(press_frame, textvariable=self.vars['press_interval']).grid(row=0, column=3, padx=5, pady=5)
        self.vars['press_interval'].trace_add("write", lambda *args: self.check_changes())

        # Serial Settings
        serial_container = ttk.Frame(self)
        serial_container.pack(fill=tk.BOTH, expand=True, pady=5)

        self.serial_frames = {}
        for idx, title in enumerate(["X-Axis Motor", "Y-Axis Motor", "Relay (Solenoid)"]):
            frame = SerialConfigFrame(serial_container, title, self.check_changes, self.port_manager, self.log)
            frame.grid(row=0, column=idx, padx=5, sticky=tk.NSEW)
            serial_container.columnconfigure(idx, weight=1)
            self.serial_frames[title] = frame

        # Apply Button
        self.btn_apply = ttk.Button(self, text="Apply Changes", command=self.apply_changes, state=tk.DISABLED)
        self.btn_apply.pack(side=tk.BOTTOM, pady=10, anchor=tk.E)

        # Initial visibility check
        self.on_mode_change()

    def on_mode_change(self):
        mode = self.vars['test_mode'].get()
        if mode == 'time':
            self.unit_combo.grid() # Show
        else:
            self.unit_combo.grid_remove() # Hide
        self.check_changes()

    def get_current_state(self):
        state = {key: var.get() for key, var in self.vars.items()}
        # Add serial states
        for title, frame in self.serial_frames.items():
            state[title] = frame.get_settings()
        return state

    def save_initial_state(self):
        self.saved_state = copy.deepcopy(self.get_current_state())

    def check_changes(self, *args):
        if not hasattr(self, 'saved_state'):
            return
        current_state = self.get_current_state()
        if current_state != self.saved_state:
            self.btn_apply.state(['!disabled'])
        else:
            self.btn_apply.state(['disabled'])

    def apply_changes(self):
        self.save_initial_state()
        self.check_changes()
        self.log(f"Settings Applied: {self.saved_state}", "SET")

    def get_serial_connection(self, title):
        if title in self.serial_frames:
            return self.serial_frames[title].get_serial_connection()
        return None
