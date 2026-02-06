import tkinter as tk
from tkinter import ttk
import copy
import serial
import serial.tools.list_ports
from config_manager import ConfigManager
from key_manager import KeyManager

# =========================================================================
# 辅助类：测试项设置窗口 (TestItemSettingsWindow)
# =========================================================================
class TestItemSettingsWindow(tk.Toplevel):
    """
    TestItemSettingsWindow 类：新增测试项时的设置窗口。
    """
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Add Test Item")
        self.geometry("420x350")
        self.callback = callback
        self.key_manager = KeyManager()
        
        # 设置窗口背景色
        self.configure(bg="#f3f2f1")
        
        self.setup_ui()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. 测试类型 (Test Type)
        ttk.Label(main_frame, text="Test Type:", font=("Cambria", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=8)
        self.type_var = tk.StringVar(value="single")
        type_frame = ttk.Frame(main_frame)
        type_frame.grid(row=0, column=1, sticky=tk.W, pady=8)
        ttk.Radiobutton(type_frame, text="Single Key", variable=self.type_var, value="single").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_frame, text="Multi-Key", variable=self.type_var, value="multi").pack(side=tk.LEFT, padx=5)

        # 2. 选择按键
        ttk.Label(main_frame, text="Select Key:", font=("Cambria", 9, "bold")).grid(row=1, column=0, sticky=tk.W, pady=8)
        self.key_var = tk.StringVar()
        bindings = self.key_manager.get_bindings()
        key_names = [b['key_name'] for b in bindings]
        self.key_combo = ttk.Combobox(main_frame, textvariable=self.key_var, values=key_names, state="readonly")
        self.key_combo.grid(row=1, column=1, sticky=tk.EW, pady=8)
        if key_names:
            self.key_combo.current(0)
            
        # 3. 测试模式
        ttk.Label(main_frame, text="Test Mode:", font=("Cambria", 9, "bold")).grid(row=2, column=0, sticky=tk.W, pady=8)
        self.mode_var = tk.StringVar(value="count")
        mode_frame = ttk.Frame(main_frame)
        mode_frame.grid(row=2, column=1, sticky=tk.W, pady=8)
        ttk.Radiobutton(mode_frame, text="Count", variable=self.mode_var, value="count", command=self.on_mode_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="Time", variable=self.mode_var, value="time", command=self.on_mode_change).pack(side=tk.LEFT, padx=5)
        
        # 4. 目标数值
        ttk.Label(main_frame, text="Target Value:", font=("Cambria", 9, "bold")).grid(row=3, column=0, sticky=tk.W, pady=8)
        self.target_var = tk.IntVar(value=100)
        self.target_entry = ttk.Entry(main_frame, textvariable=self.target_var)
        self.target_entry.grid(row=3, column=1, sticky=tk.EW, pady=8)
        
        # 5. 时间单位
        self.unit_label = ttk.Label(main_frame, text="Unit:", font=("Cambria", 9, "bold"))
        self.unit_var = tk.StringVar(value="Seconds")
        self.unit_combo = ttk.Combobox(main_frame, textvariable=self.unit_var, values=["Seconds", "Minutes", "Hours"], state="readonly")
        
        # 6. 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=25)
        ttk.Button(btn_frame, text="OK", style="Primary.TButton", width=12, command=self.on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Cancel", width=12, command=self.destroy).pack(side=tk.LEFT, padx=10)
        
        self.on_mode_change()
        
    def on_mode_change(self):
        if self.mode_var.get() == "time":
            self.unit_label.grid(row=4, column=0, sticky=tk.W, pady=5)
            self.unit_combo.grid(row=4, column=1, sticky=tk.EW, pady=5)
        else:
            self.unit_label.grid_remove()
            self.unit_combo.grid_remove()
            
    def on_ok(self):
        key_name = self.key_var.get()
        if not key_name:
            return
            
        test_item = {
            "type": self.type_var.get(),
            "key_name": key_name,
            "mode": self.mode_var.get(),
            "target": self.target_var.get(),
            "unit": self.unit_var.get() if self.mode_var.get() == "time" else ""
        }
        self.callback(test_item)
        self.destroy()

# =========================================================================
# 辅助类：串口配置组件 (SerialConfigFrame)
# =========================================================================
class SerialConfigFrame(ttk.LabelFrame):
    """
    SerialConfigFrame 类：通用的串口配置子组件，继承自 ttk.LabelFrame。
    包含端口选择、波特率配置及打开/关闭逻辑。简化了数据位、停止位和校验位（默认为 8-N-1）。
    """
    def __init__(self, master, title, on_change_callback, port_manager, log_callback):
        """
        参数:
            master: 父级容器
            title: 标签框架的标题
            on_change_callback: 配置改变时的回调函数（用于更新“应用”按钮状态）
            port_manager: 端口管理器实例，用于检查端口冲突
            log_callback: 日志记录回调函数
        """
        super().__init__(master, text=title, padding=15)
        self.on_change = on_change_callback
        self.port_manager = port_manager
        self.log = log_callback
        self.serial_conn = None # 存储实际的 serial.Serial 连接对象
        self.is_open = False    # 标记当前串口是否已打开
        
        # 内部变量（保持兼容性）
        self.data_bits_var = tk.IntVar(value=8)
        self.stop_bits_var = tk.DoubleVar(value=1)
        self.parity_var = tk.StringVar(value='None')
        
        self.create_widgets()

    def create_widgets(self):
        """
        创建并布局串口配置相关的 UI 组件。
        """
        # 设置网格布局权重，使输入框可拉伸
        self.columnconfigure(1, weight=1)

        # 1. 端口选择 (Port Selection)
        ttk.Label(self, text="Port:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(self, textvariable=self.port_var, state="readonly")
        self.port_combo.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        # 绑定选择事件
        self.port_combo.bind("<<ComboboxSelected>>", lambda e: self.on_change())
        # 绑定鼠标点击事件，实时刷新可用端口
        self.port_combo.bind('<Button-1>', self.refresh_ports) 

        # 2. 波特率 (Baud Rate)
        ttk.Label(self, text="Baud:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.baud_var = tk.IntVar(value=9600)
        self.baud_combo = ttk.Combobox(self, textvariable=self.baud_var, values=[9600, 19200, 38400, 115200], state="readonly")
        self.baud_combo.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        self.baud_combo.bind("<<ComboboxSelected>>", lambda e: self.on_change())

        # 3. 打开/关闭端口按钮 (Open/Close Button)
        self.btn_open = ttk.Button(self, text="Open Port", style="Primary.TButton", command=self.toggle_port)
        self.btn_open.grid(row=2, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=10)
        
        # 初始刷新一次端口
        self.refresh_ports()

    def refresh_ports(self, event=None):
        """
        枚举当前系统所有可用的串口。
        """
        ports = sorted([port.device for port in serial.tools.list_ports.comports()])
        if not ports:
            self.port_combo['values'] = []
            if not self.port_var.get():
                self.port_combo.set('')
        else:
            self.port_combo['values'] = ports

    def toggle_port(self):
        """
        切换串口状态：如果已打开则关闭，反之则尝试打开。
        """
        if self.is_open:
            # --- 关闭逻辑 ---
            if self.serial_conn and self.serial_conn.is_open:
                try:
                    self.serial_conn.close()
                except Exception as e:
                    self.log(f"Error closing port: {e}", "ERR")
            self.serial_conn = None
            # 释放端口管理器中的占用
            self.port_manager.release_port(self.port_var.get())
            self.is_open = False
            self.btn_open.config(text="Open Port", style="Primary.TButton")
            self.log(f"{self['text']} Port Closed", "SER")
            self.toggle_inputs(True) # 恢复输入框为可编辑
        else:
            # --- 打开逻辑 ---
            port = self.port_var.get()
            if not port:
                self.log("Error: No port selected", "ERR")
                return
            
            # 检查该端口是否已被本项目其他实例占用
            if not self.port_manager.is_port_available(port):
                self.log(f"Error: Port {port} is already in use", "ERR")
                return

            try:
                # 实例化串口对象并尝试打开
                self.serial_conn = serial.Serial(
                    port=port,
                    baudrate=self.baud_var.get(),
                    bytesize=8,
                    stopbits=1,
                    parity=serial.PARITY_NONE,
                    timeout=0.1
                )
                
                # 标记端口为占用状态
                self.port_manager.claim_port(port)
                self.is_open = True
                self.btn_open.config(text="Close Port", style="Danger.TButton")
                self.log(f"{self['text']} Port {port} Opened successfully", "SER")
                self.toggle_inputs(False) # 禁用配置输入框，防止运行时修改
            except Exception as e:
                self.log(f"Error opening port {port}: {e}", "ERR")
                self.serial_conn = None

    def toggle_inputs(self, enable):
        """
        统一设置所有配置输入框的启用/禁用状态。
        """
        state = "readonly" if enable else "disabled"
        self.port_combo.config(state=state)
        self.baud_combo.config(state=state)

    def get_settings(self):
        """获取当前组件的配置字典"""
        return {
            'port': self.port_var.get(),
            'baud': self.baud_var.get(),
            'data_bits': 8,
            'stop_bits': 1,
            'parity': 'None'
        }

    def get_serial_connection(self):
        """获取当前已打开的串口连接对象"""
        return self.serial_conn

# =========================================================================
# 辅助类：全局端口管理器 (PortManager)
# =========================================================================
class PortManager:
    """
    PortManager 类：简单的辅助类，用于防止同一个串口被分配给不同的轴。
    """
    def __init__(self):
        self.used_ports = set()

    def is_port_available(self, port):
        """检查端口是否空闲"""
        return port not in self.used_ports

    def claim_port(self, port):
        """占用端口"""
        self.used_ports.add(port)

    def release_port(self, port):
        """释放端口"""
        if port in self.used_ports:
            self.used_ports.remove(port)

# =========================================================================
# 主界面类：设置页签 (SettingsFrame)
# =========================================================================
class SettingsFrame(ttk.Frame):
    """
    SettingsFrame 类：参数设置页签界面，继承自 ttk.Frame。
    负责管理测试模式、测试参数、电机及继电器串口配置。
    """
    def __init__(self, master=None, log_callback=None):
        super().__init__(master)
        # --- 成员变量初始化 ---
        self.log = log_callback if log_callback else print
        self.port_manager = PortManager() # 初始化端口管理器
        self.vars = {} # 存储普通参数的变量字典
        self.config_manager = ConfigManager() # 初始化配置管理器
        self.test_flow = [] # 存储测试流程项
        self.test_control = None # 引用测试控制对象
        
        self.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建界面组件
        self.create_widgets()
        
        # 尝试加载保存的配置
        self.load_config()
        
        # 记录初始状态，用于对比是否有未保存的更改
        self.save_initial_state()

    def create_widgets(self):
        """
        创建设置页面的所有组件分区。
        布局顺序调整为：1. 串口配置 2. 按压参数 3. 测试流程（最底部）
        """
        # --- 1. 串口配置分区 (Serial Settings) ---
        serial_container = ttk.Frame(self)
        serial_container.pack(fill=tk.X, pady=(0, 10))

        self.serial_frames = {}
        for idx, title in enumerate(["X-Axis Motor", "Y-Axis Motor", "Relay (Solenoid)"]):
            # 使用包装框架以便更好控制 padding
            wrapper = ttk.Frame(serial_container)
            wrapper.grid(row=0, column=idx, padx=5, sticky=tk.NSEW)
            serial_container.columnconfigure(idx, weight=1)
            
            frame = SerialConfigFrame(wrapper, title, self.check_changes, self.port_manager, self.log)
            frame.pack(fill=tk.BOTH, expand=True)
            self.serial_frames[title] = frame

        # --- 2. 按压参数设置分区 (Press Settings) ---
        press_card = tk.Frame(self, bg="white", highlightthickness=1, highlightbackground="#edebe9")
        press_card.pack(fill=tk.X, pady=10)
        
        # 标题栏
        press_title_bar = tk.Frame(press_card, bg="#f8f9fa")
        press_title_bar.pack(fill=tk.X)
        tk.Label(press_title_bar, text="Press Settings", font=("Cambria", 10, "bold"), bg="#f8f9fa", fg="#323130").pack(side=tk.LEFT, padx=15, pady=8)

        # 输入区域
        press_inner = tk.Frame(press_card, bg="white", padx=20, pady=15)
        press_inner.pack(fill=tk.X)

        # Press Duration
        tk.Label(press_inner, text="Press Duration (ms):", font=("Cambria", 9), bg="white", fg="#605e5c").grid(row=0, column=0, padx=(0, 10), pady=5, sticky=tk.W)
        self.vars['press_duration'] = tk.IntVar(value=100)
        ttk.Entry(press_inner, textvariable=self.vars['press_duration'], width=15).grid(row=0, column=1, padx=(0, 20), pady=5)
        self.vars['press_duration'].trace_add("write", lambda *args: self.check_changes())

        # Interval
        tk.Label(press_inner, text="Interval (ms):", font=("Cambria", 9), bg="white", fg="#605e5c").grid(row=0, column=2, padx=(0, 10), pady=5, sticky=tk.W)
        self.vars['press_interval'] = tk.IntVar(value=500)
        ttk.Entry(press_inner, textvariable=self.vars['press_interval'], width=15).grid(row=0, column=3, padx=(0, 20), pady=5)
        self.vars['press_interval'].trace_add("write", lambda *args: self.check_changes())

        # --- 3. 测试流程设置分区 (Test Flow) ---
        flow_card = tk.Frame(self, bg="white", highlightthickness=1, highlightbackground="#edebe9")
        flow_card.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # 标题栏
        flow_title_bar = tk.Frame(flow_card, bg="#f8f9fa")
        flow_title_bar.pack(fill=tk.X)
        tk.Label(flow_title_bar, text="Test Flow", font=("Cambria", 10, "bold"), bg="#f8f9fa", fg="#323130").pack(side=tk.LEFT, padx=15, pady=8)

        # 控制栏
        ctrl_frame = tk.Frame(flow_card, bg="white", padx=15, pady=10)
        ctrl_frame.pack(fill=tk.X)

        self.btn_add = ttk.Button(ctrl_frame, text="+ Add Test Item", style="Primary.TButton", command=self.open_add_test_item_window)
        self.btn_add.pack(side=tk.LEFT, padx=5)

        self.btn_clear = ttk.Button(ctrl_frame, text="Clear All", style="Danger.TButton", command=self.clear_test_flow)
        self.btn_clear.pack(side=tk.LEFT, padx=5)

        self.btn_next = ttk.Button(ctrl_frame, text="Next Item >>", command=self.skip_to_next_item, state=tk.DISABLED)
        self.btn_next.pack(side=tk.RIGHT, padx=5)

        # 测试项显示区域
        self.flow_canvas = tk.Canvas(flow_card, height=180, highlightthickness=0, bg="white")
        self.flow_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5)
        
        scrollbar = ttk.Scrollbar(flow_card, orient=tk.HORIZONTAL, command=self.flow_canvas.xview)
        scrollbar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0, 5))
        self.flow_canvas.configure(xscrollcommand=scrollbar.set)

        self.flow_container = tk.Frame(self.flow_canvas, bg="white")
        self.flow_canvas.create_window((0, 0), window=self.flow_container, anchor=tk.NW)
        
        self.flow_container.bind("<Configure>", lambda e: self.flow_canvas.configure(scrollregion=self.flow_canvas.bbox("all")))

        # --- 4. 应用按钮 (底部) ---
        self.btn_apply = ttk.Button(self, text="Apply Changes", style="Primary.TButton", command=self.apply_changes, state=tk.DISABLED)
        self.btn_apply.pack(side=tk.BOTTOM, pady=(10, 0), anchor=tk.E)

    def open_add_test_item_window(self):
        """打开新增测试项窗口"""
        TestItemSettingsWindow(self, self.add_test_item)

    def add_test_item(self, item):
        """回调函数：添加测试项到流程"""
        self.test_flow.append(item)
        self.render_test_flow()
        self.check_changes()

    def delete_test_item(self, index):
        """删除指定的测试项"""
        if 0 <= index < len(self.test_flow):
            self.test_flow.pop(index)
            self.render_test_flow()
            self.check_changes()

    def render_test_flow(self):
        """渲染测试流程区域的所有测试项"""
        is_testing = False
        current_idx = -1
        if self.test_control:
            is_testing = self.test_control.is_running
            current_idx = self.test_control.current_item_index

        self.btn_clear.config(state=tk.DISABLED if is_testing else tk.NORMAL)
        self.btn_next.config(state=tk.NORMAL if is_testing else tk.DISABLED)

        for widget in self.flow_container.winfo_children():
            widget.destroy()

        for i, item in enumerate(self.test_flow):
            if i > 0:
                arrow_label = tk.Label(self.flow_container, text="➜", font=("Cambria", 18), fg="#0078d4", bg="white")
                arrow_label.pack(side=tk.LEFT, padx=5)

            # 样式定义
            status_text = ""
            status_color = "white"
            border_color = "#edebe9"
            header_bg = "#f8f9fa"
            text_color = "#323130"
            
            if is_testing:
                if i < current_idx:
                    status_text = "Completed"
                    header_bg = "#e1dfdd"
                    text_color = "#605e5c"
                elif i == current_idx:
                    status_text = "Running..."
                    header_bg = "#dff6dd" # 浅绿
                    border_color = "#107c10"
                    text_color = "#107c10"
                    status_color = "#f3fdf3"
                else:
                    status_text = "Pending"
            
            # 创建卡片容器
            card = tk.Frame(self.flow_container, bg=status_color, highlightthickness=1, highlightbackground=border_color)
            card.pack(side=tk.LEFT, padx=10, pady=20, ipadx=10, ipady=10)
            
            # 卡片标题栏
            header = tk.Frame(card, bg=header_bg)
            header.pack(fill=tk.X)
            
            tk.Label(header, text=f"Step {i+1}", font=("Cambria", 9, "bold"), bg=header_bg, fg=text_color).pack(side=tk.LEFT, padx=8, pady=4)
            if status_text:
                tk.Label(header, text=status_text, font=("Cambria", 8, "italic"), bg=header_bg, fg=text_color).pack(side=tk.RIGHT, padx=8)

            # 内容区域
            content = tk.Frame(card, bg=status_color)
            content.pack(fill=tk.BOTH, expand=True, pady=10)

            tk.Label(content, text=item['key_name'], font=("Cambria", 12, "bold"), bg=status_color, fg=text_color).pack(pady=(5, 2))
            
            val_text = f"{item['target']} {item['unit'] if item['mode'] == 'time' else 'Times'}"
            tk.Label(content, text=val_text, font=("Cambria", 10), bg=status_color, fg="#605e5c").pack()
            
            type_text = "Single Key" if item.get('type') == 'single' else "Multi-Key"
            tk.Label(content, text=type_text, font=("Cambria", 8), bg=status_color, fg="#a19f9d").pack(pady=5)

            # 右键菜单 (仅在非测试时或特定条件下允许删除)
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Delete Item", command=lambda idx=i: self.delete_test_item(idx))
            
            def show_menu(event, m=menu, idx=i):
                if is_testing and idx <= current_idx:
                    return
                m.post(event.x_root, event.y_root)
            
            card.bind("<Button-3>", show_menu)
            for child in card.winfo_children():
                child.bind("<Button-3>", show_menu)
                for grand_child in child.winfo_children():
                    grand_child.bind("<Button-3>", show_menu)

    def clear_test_flow(self):
        """清空所有测试项"""
        if self.test_control and self.test_control.is_running:
            return
        self.test_flow = []
        self.render_test_flow()
        self.check_changes()

    def skip_to_next_item(self):
        """跳过当前测试项"""
        if self.test_control:
            self.test_control.skip_to_next()

    def show_context_menu(self, event, index):
        """显示右键删除菜单"""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Delete", command=lambda: self.delete_test_item(index))
        menu.post(event.x_root, event.y_root)

    def on_mode_change(self):
        """测试模式切换时的 UI 响应 (已废弃，保留空函数以防其他地方调用)"""
        pass

    def get_current_state(self):
        """
        快照当前所有设置项的数值。
        处理空值情况，避免转换异常。
        """
        state = {}
        for key, var in self.vars.items():
            try:
                state[key] = var.get()
            except:
                # 如果变量为空或转换失败，使用默认值
                if key == 'press_duration':
                    state[key] = 100
                elif key == 'press_interval':
                    state[key] = 500
                else:
                    state[key] = var.get() if hasattr(var, 'get') else ""
        
        # 合并三个串口组件的配置
        for title, frame in self.serial_frames.items():
            state[title] = frame.get_settings()
            
        # 添加测试流程配置
        state['test_flow'] = copy.deepcopy(self.test_flow)
        return state

    def save_initial_state(self):
        """保存当前状态作为“已应用”基准线"""
        self.saved_state = copy.deepcopy(self.get_current_state())

    def check_changes(self, *args):
        """
        对比当前状态与保存的状态，决定“应用”按钮是否可用。
        """
        if not hasattr(self, 'saved_state'):
            return
        current_state = self.get_current_state()
        if current_state != self.saved_state:
            self.btn_apply.state(['!disabled']) # 启用按钮
        else:
            self.btn_apply.state(['disabled'])  # 禁用按钮

    def apply_changes(self):
        """
        点击"应用"按钮后的处理逻辑。
        验证输入的有效性，如果输入无效则恢复为上一次保存的值。
        """
        # 验证并修复无效的输入
        self.validate_and_fix_inputs()
        
        # 保存初始状态
        self.save_initial_state()
        self.check_changes()
        self.log(f"Settings Applied: {self.saved_state}", "SET")
        
        # 自动保存配置到文件
        self.save_config_to_file()
    
    def validate_and_fix_inputs(self):
        """
        验证输入的有效性，如果输入无效则恢复为上一次保存的值。
        检查的字段包括：press_duration, press_interval
        """
        # 获取上一次保存的值（如果有）
        last_press_duration = self.saved_state.get('press_duration', 100) if hasattr(self, 'saved_state') else 100
        last_press_interval = self.saved_state.get('press_interval', 500) if hasattr(self, 'saved_state') else 500
        
        # 验证并修复 press_duration
        try:
            press_duration = self.vars['press_duration'].get()
            if press_duration is None or press_duration <= 0:
                raise ValueError("Invalid press duration")
        except:
            self.vars['press_duration'].set(last_press_duration)
            self.log(f"Invalid press duration, restored to {last_press_duration}", "SET")
        
        # 验证并修复 press_interval
        try:
            press_interval = self.vars['press_interval'].get()
            if press_interval is None or press_interval <= 0:
                raise ValueError("Invalid press interval")
        except:
            self.vars['press_interval'].set(last_press_interval)
            self.log(f"Invalid press interval, restored to {last_press_interval}", "SET")

    def save_config_to_file(self):
        """将当前配置保存到文件"""
        config = self.get_current_state()
        
        # 过滤掉空值，确保配置文件中不包含空值
        filtered_config = {}
        for key, value in config.items():
            if value is None or value == "":
                continue
            if isinstance(value, dict):
                # 对于字典类型的配置（如串口配置），也进行过滤
                filtered_dict = {}
                for sub_key, sub_value in value.items():
                    if sub_value is not None and sub_value != "":
                        filtered_dict[sub_key] = sub_value
                if filtered_dict:  # 只有当字典不为空时才添加
                    filtered_config[key] = filtered_dict
            else:
                filtered_config[key] = value
        
        if self.config_manager.save_config(filtered_config):
            self.log(f"Configuration saved to {self.config_manager.get_config_file_path()}", "SET")
        else:
            self.log("Failed to save configuration", "ERR")

    def load_config(self):
        """从文件加载配置"""
        config = self.config_manager.load_config()
        if config is None:
            self.log("No saved configuration found, using defaults", "SET")
            return
        
        try:
            # 加载普通参数，使用默认值防止空值
            if 'press_duration' in config and config['press_duration'] is not None:
                self.vars['press_duration'].set(config['press_duration'])
            
            if 'press_interval' in config and config['press_interval'] is not None:
                self.vars['press_interval'].set(config['press_interval'])
            
            # 加载测试流程
            if 'test_flow' in config:
                self.test_flow = config['test_flow']
                self.render_test_flow()

            # 加载串口配置
            for title, frame in self.serial_frames.items():
                if title in config:
                    serial_config = config[title]
                    if serial_config and 'port' in serial_config and serial_config['port']:
                        frame.port_var.set(serial_config['port'])
                    if serial_config and 'baud' in serial_config and serial_config['baud'] is not None:
                        frame.baud_var.set(serial_config['baud'])
                    if serial_config and 'data_bits' in serial_config and serial_config['data_bits'] is not None:
                        frame.data_bits_var.set(serial_config['data_bits'])
                    if serial_config and 'stop_bits' in serial_config and serial_config['stop_bits'] is not None:
                        frame.stop_bits_var.set(serial_config['stop_bits'])
                    if serial_config and 'parity' in serial_config and serial_config['parity']:
                        frame.parity_var.set(serial_config['parity'])
            
            self.log(f"Configuration loaded from {self.config_manager.get_config_file_path()}", "SET")
            
            # 更新UI显示
            # self.on_mode_change()
            
        except Exception as e:
            self.log(f"Error loading configuration: {e}", "ERR")

    def get_serial_connection(self, title):
        """
        供外部(如测试控制页)调用的接口，用于获取已打开的串口连接。
        """
        if title in self.serial_frames:
            return self.serial_frames[title].get_serial_connection()
        return None
