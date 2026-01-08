import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import datetime

class LogFrame(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.all_logs = [] # List of tuples: (datetime_obj, category_str, message_str, full_entry_str)
        self.categories = ['SYS', 'MOT', 'SET', 'SER', 'TEST', 'REL', 'ERR']
        self.is_filtered = False
        self.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.create_widgets()
        self.add_mock_logs()

    def create_widgets(self):
        # Toolbar
        self.toolbar = ttk.Frame(self)
        self.toolbar.pack(fill=tk.X, pady=(0, 5))

        # Filter Button (Light Blue)
        self.btn_filter = tk.Button(
            self.toolbar,
            text="Filter",
            command=self.open_filter_window,
            bg="#ADD8E6", # Light Blue
            fg="white",
            font=("Cambria", 10, "bold"),
            relief=tk.FLAT,
            padx=15
        )
        self.btn_filter.pack(side=tk.LEFT, padx=5)

        # Recover Button (Initially hidden)
        self.btn_recover = tk.Button(
            self.toolbar,
            text="Recover",
            command=self.recover_logs,
            bg="#90EE90", # Light Green
            fg="white",
            font=("Cambria", 10, "bold"),
            relief=tk.FLAT,
            padx=15
        )
        # We'll pack it only when filtered

        # Using tk.Button for easier background/foreground color control
        self.btn_export = tk.Button(
            self.toolbar, 
            text="Export Log", 
            command=self.export_log,
            bg="black",
            fg="white",
            font=("Cambria", 10),
            relief=tk.FLAT,
            padx=10
        )
        self.btn_export.pack(side=tk.RIGHT, padx=5)

        self.btn_clear = tk.Button(
            self.toolbar, 
            text="Clear Log", 
            command=self.clear_log_with_confirm,
            bg="red",
            fg="white",
            font=("Cambria", 10),
            relief=tk.FLAT,
            padx=10
        )
        self.btn_clear.pack(side=tk.RIGHT, padx=5)

        # Log Area
        self.log_area = scrolledtext.ScrolledText(self, state='disabled', height=20, font=("Cambria", 10))
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def add_log(self, message, category="SYS"):
        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S") + f".{now.microsecond // 1000:03d}"
        entry = f"[{timestamp_str}] [{category}] {message}\n"
        
        # Store in memory
        self.all_logs.append((now, category, message, entry))
        
        # Display only if not filtered (or we could re-apply filter, but usually new logs show up)
        if not self.is_filtered:
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, entry)
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')

    def add_mock_logs(self):
        self.add_log("System initialized.", "SYS")
        self.add_log("Loading configuration...", "SYS")
        self.add_log("Connecting to Motion Controller...", "MOT")
        self.add_log("Motion Controller connected.", "MOT")
        self.add_log("Checking settings...", "SET")
        self.add_log("Ready for operation.", "SYS")
        self.add_log("Starting test sequence...", "TEST")
        self.add_log("Error: Sensor timeout.", "ERR")

    def recover_logs(self):
        self.is_filtered = False
        self.btn_recover.pack_forget()
        self.apply_filter(None, None, "", "")

    def clear_log_with_confirm(self):
        if not self.all_logs:
            return

        answer = messagebox.askyesnocancel("Clear Log", "Do you want to save the logs before clearing?")
        
        if answer is True: # Yes
            # Export visible logs (filtered or all)
            if self.export_log():
                self.perform_clear()
        elif answer is False: # No
            self.perform_clear()

    def perform_clear(self):
        self.all_logs = []
        self.is_filtered = False
        self.btn_recover.pack_forget()
        self.log_area.config(state='normal')
        self.log_area.delete("1.0", tk.END)
        self.log_area.config(state='disabled')
        self.add_log("Log cleared.", "SYS")

    def export_log(self):
        default_filename = "test_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=default_filename,
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                # Export ONLY visible content from log_area
                content = self.log_area.get("1.0", tk.END)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.add_log(f"Log exported to {file_path}", "SYS")
                return True
            except Exception as e:
                self.add_log(f"Error exporting log: {e}", "ERR")
                return False
        return False

    def open_filter_window(self):
        filter_win = tk.Toplevel(self)
        filter_win.title("Filter Logs")
        filter_win.geometry("550x500")
        filter_win.resizable(False, False)
        filter_win.configure(bg="white")
        filter_win.transient(self.winfo_toplevel())
        filter_win.grab_set()

        # Time Picker Helper
        def create_time_picker(parent, title):
            frame = ttk.LabelFrame(parent, text=title, padding=5)
            frame.pack(fill=tk.X, padx=10, pady=2)
            
            now = datetime.datetime.now()
            
            # Years (Current +/- 5)
            years = [str(y) for y in range(now.year - 5, now.year + 6)]
            months = [f"{m:02d}" for m in range(1, 13)]
            days = [f"{d:02d}" for d in range(1, 32)]
            hours = [f"{h:02d}" for h in range(0, 24)]
            min_sec = [f"{i:02d}" for i in range(0, 60)]

            vars = {
                'Y': tk.StringVar(), 'M': tk.StringVar(), 'D': tk.StringVar(),
                'h': tk.StringVar(), 'm': tk.StringVar(), 's': tk.StringVar()
            }

            # Layout
            ttk.Combobox(frame, textvariable=vars['Y'], values=years, width=5, state="readonly").pack(side=tk.LEFT, padx=2)
            ttk.Label(frame, text="-").pack(side=tk.LEFT)
            ttk.Combobox(frame, textvariable=vars['M'], values=months, width=3, state="readonly").pack(side=tk.LEFT, padx=2)
            ttk.Label(frame, text="-").pack(side=tk.LEFT)
            ttk.Combobox(frame, textvariable=vars['D'], values=days, width=3, state="readonly").pack(side=tk.LEFT, padx=2)
            
            ttk.Label(frame, text=" ").pack(side=tk.LEFT, padx=5)
            
            ttk.Combobox(frame, textvariable=vars['h'], values=hours, width=3, state="readonly").pack(side=tk.LEFT, padx=2)
            ttk.Label(frame, text=":").pack(side=tk.LEFT)
            # Min/Sec are editable
            ttk.Combobox(frame, textvariable=vars['m'], values=min_sec, width=3).pack(side=tk.LEFT, padx=2)
            ttk.Label(frame, text=":").pack(side=tk.LEFT)
            ttk.Combobox(frame, textvariable=vars['s'], values=min_sec, width=3).pack(side=tk.LEFT, padx=2)
            
            return vars

        start_vars = create_time_picker(filter_win, "Start Time (From)")
        end_vars = create_time_picker(filter_win, "End Time (To)")

        def set_vars_from_dt(vars_dict, dt):
            vars_dict['Y'].set(str(dt.year))
            vars_dict['M'].set(f"{dt.month:02d}")
            vars_dict['D'].set(f"{dt.day:02d}")
            vars_dict['h'].set(f"{dt.hour:02d}")
            vars_dict['m'].set(f"{dt.minute:02d}")
            vars_dict['s'].set(f"{dt.second:02d}")

        def get_dt_from_vars(vars_dict):
            try:
                y, m, d = vars_dict['Y'].get(), vars_dict['M'].get(), vars_dict['D'].get()
                h, mi, s = vars_dict['h'].get(), vars_dict['m'].get(), vars_dict['s'].get()
                if not all([y, m, d, h, mi, s]): return None
                return datetime.datetime(int(y), int(m), int(d), int(h), int(mi), int(s))
            except: return None

        def init_time():
            now = datetime.datetime.now()
            hour_ago = now - datetime.timedelta(hours=1)
            set_vars_from_dt(start_vars, hour_ago)
            set_vars_from_dt(end_vars, now)

        btn_init_time = ttk.Button(filter_win, text="Init Time", command=init_time)
        btn_init_time.pack(pady=5)

        # Category
        cat_frame = ttk.LabelFrame(filter_win, text="Category Tag", padding=10)
        cat_frame.pack(fill=tk.X, padx=10, pady=5)
        cat_var = tk.StringVar()
        cat_combo = ttk.Combobox(cat_frame, textvariable=cat_var, values=self.categories)
        cat_combo.pack(fill=tk.X)

        # Content
        content_frame = ttk.LabelFrame(filter_win, text="Log Content Keyword", padding=10)
        content_frame.pack(fill=tk.X, padx=10, pady=5)
        content_var = tk.StringVar()
        ent_content = ttk.Entry(content_frame, textvariable=content_var)
        ent_content.pack(fill=tk.X)

        # Action Buttons
        btn_action_frame = ttk.Frame(filter_win, padding=10)
        btn_action_frame.pack(fill=tk.X, side=tk.BOTTOM)

        def reset_filters_ui():
            # Only reset UI components, don't affect main log display
            for v in list(start_vars.values()) + list(end_vars.values()): v.set("")
            cat_var.set("")
            content_var.set("")

        def apply_filter_action():
            s_time = get_dt_from_vars(start_vars)
            e_time = get_dt_from_vars(end_vars)
            
            if (start_vars['Y'].get() and not s_time) or (end_vars['Y'].get() and not e_time):
                messagebox.showerror("Error", "Invalid time format.")
                return
                
            if s_time and e_time and s_time > e_time:
                messagebox.showerror("Error", "Start time must be earlier than end time.")
                return

            self.is_filtered = True
            # Show recover button
            self.btn_recover.pack(side=tk.LEFT, padx=5, after=self.btn_filter)
            self.apply_filter(s_time, e_time, cat_var.get().strip(), content_var.get().strip())
            filter_win.destroy()

        btn_reset = ttk.Button(btn_action_frame, text="Reset", command=reset_filters_ui)
        btn_reset.pack(side=tk.LEFT, padx=10)

        btn_apply = ttk.Button(btn_action_frame, text="Filter", command=apply_filter_action)
        btn_apply.pack(side=tk.RIGHT, padx=10)

    def apply_filter(self, start_time, end_time, category, keyword):
        self.log_area.config(state='normal')
        self.log_area.delete("1.0", tk.END)
        
        for log_time, log_cat, log_msg, full_entry in self.all_logs:
            if start_time and log_time < start_time: continue
            if end_time and log_time > end_time: continue
            if category and category.upper() not in log_cat.upper(): continue
            if keyword and keyword.lower() not in log_msg.lower(): continue
                
            self.log_area.insert(tk.END, full_entry)
            
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
