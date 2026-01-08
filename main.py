import tkinter as tk
from tkinter import ttk
from ui_motion import MotionControlFrame
from ui_settings import SettingsFrame
from ui_test_control import TestControlFrame
from ui_log import LogFrame

class JigCtrlApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JigCtrl - Remote Control Jig System")
        self.geometry("800x600")
        
        # Apply a theme and custom styles
        self.configure_styles()

        self.create_widgets()

    def configure_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use('clam') 
        except:
            pass
        
        # Global Font and Background
        default_font = ("Cambria", 10)
        style.configure(".", font=default_font, background="white")
        
        # Specific widget configurations to ensure white background
        style.configure("TFrame", background="white")
        style.configure("TLabelframe", background="white")
        style.configure("TLabelframe.Label", background="white", font=("Cambria", 10, "bold"))
        style.configure("TLabel", background="white", font=("Cambria", 10))
        style.configure("TButton", font=("Cambria", 10), background="white")
        style.configure("Dir.TButton", font=("Cambria", 12, "bold"), background="white")
        
        # Entry and Combobox might need fieldbackground
        style.configure("TEntry", fieldbackground="white")
        style.configure("TCombobox", fieldbackground="white", background="white")
        
        # Notebook tab style
        style.configure("TNotebook", background="white")
        style.configure("TNotebook.Tab", font=("Cambria", 10))

        # Ensure the root window is also white
        self.configure(background="white")

    def create_widgets(self):
        # Main Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tabs - Initialize LogFrame first so it can be passed to others
        self.tab_log = LogFrame(self.notebook)
        
        self.tab_motion = MotionControlFrame(self.notebook, log_callback=self.tab_log.add_log)
        self.tab_settings = SettingsFrame(self.notebook, log_callback=self.tab_log.add_log)
        # Pass settings tab to test control tab so it can read configurations
        self.tab_test = TestControlFrame(self.notebook, settings_source=self.tab_settings, log_callback=self.tab_log.add_log)

        self.notebook.add(self.tab_motion, text="Motion Control (运动控制)")
        self.notebook.add(self.tab_settings, text="Parameter Settings (参数设置)")
        self.notebook.add(self.tab_test, text="Test Control (测试控制)")
        self.notebook.add(self.tab_log, text="Logs (日志)")

if __name__ == "__main__":
    app = JigCtrlApp()
    app.mainloop()
