import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import datetime

class LogFrame(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.create_widgets()
        self.add_mock_logs()

    def create_widgets(self):
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        self.btn_export = ttk.Button(toolbar, text="Export Log", command=self.export_log)
        self.btn_export.pack(side=tk.RIGHT)

        # Log Area
        self.log_area = scrolledtext.ScrolledText(self, state='disabled', height=20)
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def add_log(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}\n"
        
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, entry)
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def add_mock_logs(self):
        self.add_log("System initialized.")
        self.add_log("Loading configuration...")
        self.add_log("Ready for operation.")

    def export_log(self):
        default_filename = "test_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=default_filename,
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                content = self.log_area.get("1.0", tk.END)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.add_log(f"Log exported to {file_path}")
            except Exception as e:
                self.add_log(f"Error exporting log: {e}")
