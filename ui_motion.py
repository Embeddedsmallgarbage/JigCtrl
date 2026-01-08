import tkinter as tk
from tkinter import ttk

class MotionControlFrame(ttk.Frame):
    def __init__(self, master=None, log_callback=None):
        super().__init__(master)
        self.log = log_callback if log_callback else print
        self.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        self.create_widgets()
        self.bind_keys()

    def create_widgets(self):
        # Container for the directional buttons to center them
        self.control_container = ttk.Frame(self)
        self.control_container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Style configuration (basic)
        style = ttk.Style()
        style.configure("Dir.TButton", font=("Arial", 12, "bold"), width=8)

        # Buttons
        self.btn_up = ttk.Button(self.control_container, text="↑(Up)", style="Dir.TButton", command=lambda: self.on_btn_click('Up'))
        self.btn_left = ttk.Button(self.control_container, text="←(Left)", style="Dir.TButton", command=lambda: self.on_btn_click('Left'))
        self.btn_down = ttk.Button(self.control_container, text="↓(Down)", style="Dir.TButton", command=lambda: self.on_btn_click('Down'))
        self.btn_right = ttk.Button(self.control_container, text="→(Right)", style="Dir.TButton", command=lambda: self.on_btn_click('Right'))

        # Grid layout for cross shape
        #       Up
        # Left  Down  Right
        self.btn_up.grid(row=0, column=1, padx=5, pady=5)
        self.btn_left.grid(row=1, column=0, padx=5, pady=5)
        self.btn_down.grid(row=1, column=1, padx=5, pady=5)
        self.btn_right.grid(row=1, column=2, padx=5, pady=5)

        # Visual feedback mapping
        self.buttons = {
            'Up': self.btn_up,
            'Down': self.btn_down,
            'Left': self.btn_left,
            'Right': self.btn_right
        }

    def bind_keys(self):
        # Bind events only when this tab is visible
        self.bind('<Visibility>', self.on_visibility)
        self.bind('<Unmap>', self.on_unmap)

    def on_visibility(self, event):
        # Enable bindings
        top = self.winfo_toplevel()
        self.bind_id_press_up = top.bind('<KeyPress-Up>', lambda e: self.animate_press('Up', True))
        self.bind_id_release_up = top.bind('<KeyRelease-Up>', lambda e: self.animate_press('Up', False))
        self.bind_id_press_down = top.bind('<KeyPress-Down>', lambda e: self.animate_press('Down', True))
        self.bind_id_release_down = top.bind('<KeyRelease-Down>', lambda e: self.animate_press('Down', False))
        self.bind_id_press_left = top.bind('<KeyPress-Left>', lambda e: self.animate_press('Left', True))
        self.bind_id_release_left = top.bind('<KeyRelease-Left>', lambda e: self.animate_press('Left', False))
        self.bind_id_press_right = top.bind('<KeyPress-Right>', lambda e: self.animate_press('Right', True))
        self.bind_id_release_right = top.bind('<KeyRelease-Right>', lambda e: self.animate_press('Right', False))
        # Ensure focus so keys work if we want frame-local bindings, but top-level bindings work anyway
        self.focus_set()

    def on_unmap(self, event):
        # Disable bindings to prevent accidental motor movement in other tabs
        top = self.winfo_toplevel()
        try:
            top.unbind('<KeyPress-Up>', self.bind_id_press_up)
            top.unbind('<KeyRelease-Up>', self.bind_id_release_up)
            top.unbind('<KeyPress-Down>', self.bind_id_press_down)
            top.unbind('<KeyRelease-Down>', self.bind_id_release_down)
            top.unbind('<KeyPress-Left>', self.bind_id_press_left)
            top.unbind('<KeyRelease-Left>', self.bind_id_release_left)
            top.unbind('<KeyPress-Right>', self.bind_id_press_right)
            top.unbind('<KeyRelease-Right>', self.bind_id_release_right)
        except tk.TclError:
            pass # Ignore if already unbound

    def on_btn_click(self, direction):
        self.log(f"Button clicked: {direction}", "MOT")
        # Here logic to send serial command would be added

    def animate_press(self, direction, is_pressed):
        btn = self.buttons.get(direction)
        if not btn:
            return
        
        if is_pressed:
            btn.state(['pressed'])
            self.log(f"Key pressed: {direction}", "MOT")
        else:
            btn.state(['!pressed'])
            self.log(f"Key released: {direction}", "MOT")
