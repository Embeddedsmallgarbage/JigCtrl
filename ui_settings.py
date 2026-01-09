import tkinter as tk
from tkinter import ttk
import copy
import serial
import serial.tools.list_ports

# =========================================================================
# 辅助类：串口配置组件 (SerialConfigFrame)
# =========================================================================
class SerialConfigFrame(ttk.LabelFrame):
    """
    SerialConfigFrame 类：通用的串口配置子组件，继承自 ttk.LabelFrame。
    包含端口选择、波特率、数据位、停止位、校验位配置及打开/关闭逻辑。
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
        super().__init__(master, text=title, padding=10)
        self.on_change = on_change_callback
        self.port_manager = port_manager
        self.log = log_callback
        self.serial_conn = None # 存储实际的 serial.Serial 连接对象
        self.is_open = False    # 标记当前串口是否已打开
        
        self.create_widgets()

    def create_widgets(self):
        """
        创建并布局串口配置相关的 UI 组件。
        """
        # 设置网格布局权重，使输入框可拉伸
        self.columnconfigure(1, weight=1)

        # 1. 端口选择 (Port Selection)
        ttk.Label(self, text="Port:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(self, textvariable=self.port_var, state="readonly")
        self.port_combo.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        # 绑定选择事件
        self.port_combo.bind("<<ComboboxSelected>>", lambda e: self.on_change())
        # 绑定鼠标点击事件，实时刷新可用端口
        self.port_combo.bind('<Button-1>', self.refresh_ports) 

        # 2. 波特率 (Baud Rate)
        ttk.Label(self, text="Baud:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.baud_var = tk.IntVar(value=9600)
        self.baud_combo = ttk.Combobox(self, textvariable=self.baud_var, values=[9600, 19200, 38400, 115200], state="readonly")
        self.baud_combo.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        self.baud_combo.bind("<<ComboboxSelected>>", lambda e: self.on_change())

        # 3. 数据位 (Data Bits)
        ttk.Label(self, text="Data Bits:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.data_bits_var = tk.IntVar(value=8)
        self.data_bits_combo = ttk.Combobox(self, textvariable=self.data_bits_var, values=[5, 6, 7, 8], state="readonly")
        self.data_bits_combo.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=2)
        self.data_bits_combo.bind("<<ComboboxSelected>>", lambda e: self.on_change())

        # 4. 停止位 (Stop Bits)
        ttk.Label(self, text="Stop Bits:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.stop_bits_var = tk.DoubleVar(value=1)
        self.stop_bits_combo = ttk.Combobox(self, textvariable=self.stop_bits_var, values=[1, 1.5, 2], state="readonly")
        self.stop_bits_combo.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=2)
        self.stop_bits_combo.bind("<<ComboboxSelected>>", lambda e: self.on_change())

        # 5. 校验位 (Parity)
        ttk.Label(self, text="Parity:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.parity_var = tk.StringVar(value='None')
        self.parity_combo = ttk.Combobox(self, textvariable=self.parity_var, values=['None', 'Even', 'Odd', 'Mark', 'Space'], state="readonly")
        self.parity_combo.grid(row=4, column=1, sticky=tk.EW, padx=5, pady=2)
        self.parity_combo.bind("<<ComboboxSelected>>", lambda e: self.on_change())

        # 6. 打开/关闭端口按钮 (Open/Close Button)
        self.btn_open = ttk.Button(self, text="Open Port", command=self.toggle_port)
        self.btn_open.grid(row=5, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5)
        
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
            self.btn_open.config(text="Open Port")
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
                # 校验位映射表
                parity_map = {
                    'None': serial.PARITY_NONE,
                    'Even': serial.PARITY_EVEN,
                    'Odd': serial.PARITY_ODD,
                    'Mark': serial.PARITY_MARK,
                    'Space': serial.PARITY_SPACE
                }
                
                # 实例化串口对象并尝试打开
                self.serial_conn = serial.Serial(
                    port=port,
                    baudrate=self.baud_var.get(),
                    bytesize=self.data_bits_var.get(),
                    stopbits=self.stop_bits_var.get(),
                    parity=parity_map.get(self.parity_var.get(), serial.PARITY_NONE),
                    timeout=0.1
                )
                
                # 标记端口为占用状态
                self.port_manager.claim_port(port)
                self.is_open = True
                self.btn_open.config(text="Close Port")
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
        self.data_bits_combo.config(state=state)
        self.stop_bits_combo.config(state=state)
        self.parity_combo.config(state=state)

    def get_settings(self):
        """获取当前组件的配置字典"""
        return {
            'port': self.port_var.get(),
            'baud': self.baud_var.get(),
            'data_bits': self.data_bits_var.get(),
            'stop_bits': self.stop_bits_var.get(),
            'parity': self.parity_var.get()
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
        
        self.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建界面组件
        self.create_widgets()
        # 记录初始状态，用于对比是否有未保存的更改
        self.save_initial_state()

    def create_widgets(self):
        """
        创建设置页面的所有组件分区。
        """
        # --- 1. 测试基本参数设置分区 (Test Parameters) ---
        test_frame = ttk.LabelFrame(self, text="Test Parameters", padding=10)
        test_frame.pack(fill=tk.X, pady=5)

        # 测试模式：按次数或按时间
        self.vars['test_mode'] = tk.StringVar(value="count")
        ttk.Radiobutton(test_frame, text="By Count (Times)", variable=self.vars['test_mode'], value="count", command=self.on_mode_change).grid(row=0, column=0, padx=10, sticky=tk.W)
        ttk.Radiobutton(test_frame, text="By Time (Duration)", variable=self.vars['test_mode'], value="time", command=self.on_mode_change).grid(row=0, column=1, padx=10, sticky=tk.W)

        # 目标数值输入 (次数或时长)
        ttk.Label(test_frame, text="Target Value:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
        self.vars['target_value'] = tk.IntVar(value=100)
        entry_target = ttk.Entry(test_frame, textvariable=self.vars['target_value'])
        entry_target.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        # 追踪变量变化，实时检查是否有未保存更改
        self.vars['target_value'].trace_add("write", lambda *args: self.check_changes())

        # 时间单位选择 (仅在“按时间”模式下显示)
        self.vars['time_unit'] = tk.StringVar(value="Seconds")
        self.unit_combo = ttk.Combobox(test_frame, textvariable=self.vars['time_unit'], values=["Seconds", "Minutes", "Hours"], state="readonly", width=10)
        self.unit_combo.grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.unit_combo.bind("<<ComboboxSelected>>", lambda e: self.check_changes())
        
        # --- 2. 按压参数设置分区 (Press Settings) ---
        press_frame = ttk.LabelFrame(self, text="Press Settings", padding=10)
        press_frame.pack(fill=tk.X, pady=5)

        # 按压持续时间
        ttk.Label(press_frame, text="Press Duration (ms):").grid(row=0, column=0, padx=5, pady=5)
        self.vars['press_duration'] = tk.IntVar(value=100)
        ttk.Entry(press_frame, textvariable=self.vars['press_duration']).grid(row=0, column=1, padx=5, pady=5)
        self.vars['press_duration'].trace_add("write", lambda *args: self.check_changes())

        # 两次按压间隔
        ttk.Label(press_frame, text="Interval (ms):").grid(row=0, column=2, padx=5, pady=5)
        self.vars['press_interval'] = tk.IntVar(value=500)
        ttk.Entry(press_frame, textvariable=self.vars['press_interval']).grid(row=0, column=3, padx=5, pady=5)
        self.vars['press_interval'].trace_add("write", lambda *args: self.check_changes())

        # --- 3. 串口配置分区 (Serial Settings) ---
        serial_container = ttk.Frame(self)
        serial_container.pack(fill=tk.BOTH, expand=True, pady=5)

        self.serial_frames = {}
        # 循环创建三个串口配置块
        for idx, title in enumerate(["X-Axis Motor", "Y-Axis Motor", "Relay (Solenoid)"]):
            frame = SerialConfigFrame(serial_container, title, self.check_changes, self.port_manager, self.log)
            frame.grid(row=0, column=idx, padx=5, sticky=tk.NSEW)
            serial_container.columnconfigure(idx, weight=1)
            self.serial_frames[title] = frame

        # --- 4. 应用按钮 (底部) ---
        self.btn_apply = ttk.Button(self, text="Apply Changes", command=self.apply_changes, state=tk.DISABLED)
        self.btn_apply.pack(side=tk.BOTTOM, pady=10, anchor=tk.E)

        # 根据初始模式调整 UI 显示
        self.on_mode_change()

    def on_mode_change(self):
        """测试模式切换时的 UI 响应"""
        mode = self.vars['test_mode'].get()
        if mode == 'time':
            self.unit_combo.grid() # 显示单位选择
        else:
            self.unit_combo.grid_remove() # 隐藏单位选择
        self.check_changes()

    def get_current_state(self):
        """
        快照当前所有设置项的数值。
        """
        state = {key: var.get() for key, var in self.vars.items()}
        # 合并三个串口组件的配置
        for title, frame in self.serial_frames.items():
            state[title] = frame.get_settings()
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
        """点击“应用”按钮后的处理逻辑"""
        self.save_initial_state()
        self.check_changes()
        self.log(f"Settings Applied: {self.saved_state}", "SET")

    def get_serial_connection(self, title):
        """
        供外部(如测试控制页)调用的接口，用于获取已打开的串口连接。
        """
        if title in self.serial_frames:
            return self.serial_frames[title].get_serial_connection()
        return None
