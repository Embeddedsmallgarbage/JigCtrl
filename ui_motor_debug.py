import tkinter as tk
from tkinter import ttk, scrolledtext
import serial
import serial.tools.list_ports
import struct


class MotorDebugFrame(ttk.Frame):
    """
    MotorDebugFrame 类：电机命令调试界面，继承自 ttk.Frame。
    提供串口连接、Modbus-RTU 指令编辑发送、以及响应接收显示功能。
    """

    def __init__(self, master=None, log_callback=None):
        super().__init__(master)
        self.log = log_callback if log_callback else print
        self.serial_conn = None
        self.is_open = False

        self.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.create_widgets()

    def create_widgets(self):
        """创建调试界面的所有组件"""

        # --- 左侧：带滚动条的串口配置和快速指令区 ---
        left_container = ttk.Frame(self)
        left_container.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10), expand=False)

        # 创建 Canvas 和滚动条
        left_canvas = tk.Canvas(left_container, background="white", highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=left_canvas.yview)
        left_canvas.configure(yscrollcommand=left_scrollbar.set)

        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 在 Canvas 中创建可滚动的 Frame
        left_frame = ttk.Frame(left_canvas)
        left_canvas_window = left_canvas.create_window((0, 0), window=left_frame, anchor="nw", width=340)

        # 绑定滚动事件
        def on_frame_configure(event):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))

        def on_canvas_configure(event):
            left_canvas.itemconfig(left_canvas_window, width=event.width)

        def on_mousewheel(event):
            left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        left_frame.bind("<Configure>", on_frame_configure)
        left_canvas.bind("<Configure>", on_canvas_configure)
        left_canvas.bind_all("<MouseWheel>", on_mousewheel)

        self.left_canvas = left_canvas
        self.create_serial_config(left_frame)
        self.create_quick_commands(left_frame)
        self.create_manual_command(left_frame)

        # --- 右侧：日志显示区 ---
        right_frame = ttk.Frame(self)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.create_log_area(right_frame)

    def create_serial_config(self, parent):
        """创建串口配置区域"""
        serial_frame = ttk.LabelFrame(parent, text="Serial Port Config", padding=10)
        serial_frame.pack(fill=tk.X, pady=5)

        # 端口选择
        ttk.Label(serial_frame, text="Port:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(serial_frame, textvariable=self.port_var, state="readonly", width=15)
        self.port_combo.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        self.port_combo.bind('<Button-1>', self.refresh_ports)

        # 波特率
        ttk.Label(serial_frame, text="Baud:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.baud_var = tk.IntVar(value=9600)
        ttk.Combobox(serial_frame, textvariable=self.baud_var,
                     values=[9600, 19200, 38400, 115200], state="readonly", width=15).grid(row=1, column=1, padx=5, pady=2)

        # 数据位
        ttk.Label(serial_frame, text="Data Bits:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.data_bits_var = tk.IntVar(value=8)
        ttk.Combobox(serial_frame, textvariable=self.data_bits_var,
                     values=[5, 6, 7, 8], state="readonly", width=15).grid(row=2, column=1, padx=5, pady=2)

        # 停止位
        ttk.Label(serial_frame, text="Stop Bits:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.stop_bits_var = tk.DoubleVar(value=1)
        ttk.Combobox(serial_frame, textvariable=self.stop_bits_var,
                     values=[1, 1.5, 2], state="readonly", width=15).grid(row=3, column=1, padx=5, pady=2)

        # 校验位
        ttk.Label(serial_frame, text="Parity:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.parity_var = tk.StringVar(value='None')
        ttk.Combobox(serial_frame, textvariable=self.parity_var,
                     values=['None', 'Even', 'Odd', 'Mark', 'Space'], state="readonly", width=15).grid(row=4, column=1, padx=5, pady=2)

        # 打开/关闭按钮
        self.btn_open = ttk.Button(serial_frame, text="Open Port", command=self.toggle_port)
        self.btn_open.grid(row=5, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=10)

        # 设备地址 (固定值 0x01) 和获取所有参数按钮
        addr_frame = ttk.Frame(serial_frame)
        addr_frame.grid(row=6, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=2)

        ttk.Label(addr_frame, text="Device Addr: 0x01").pack(side=tk.LEFT)
        self.btn_get_all = ttk.Button(addr_frame, text="Get All Params", command=self.get_all_parameters,
                                      width=14)
        self.btn_get_all.pack(side=tk.RIGHT)
        self.device_addr = 0x01

        self.refresh_ports(initial=True)

    def create_quick_commands(self, parent):
        """创建快速指令按钮区域"""
        quick_frame = ttk.LabelFrame(parent, text="Quick Commands", padding=10)
        quick_frame.pack(fill=tk.X, pady=5)

        # 运行控制
        control_frame = ttk.Frame(quick_frame)
        control_frame.pack(fill=tk.X, pady=2)

        ttk.Button(control_frame, text="Run", command=lambda: self.send_quick_command(0x02, 1),
                   width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Pause", command=lambda: self.send_quick_command(0x02, 0),
                   width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Stop", command=lambda: self.send_quick_command(0x03, 1),
                   width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Get Status", command=lambda: self.send_query_command(0x02),
                   width=10).pack(side=tk.LEFT, padx=2)

        # 方向控制
        dir_frame = ttk.Frame(quick_frame)
        dir_frame.pack(fill=tk.X, pady=2)

        ttk.Label(dir_frame, text="Dir(0=CCW,1=CW):").pack(side=tk.LEFT, padx=2)
        self.dir_var = tk.IntVar(value=1)
        self.dir_spinbox = ttk.Spinbox(dir_frame, from_=0, to=1, textvariable=self.dir_var,
                    width=5)
        self.dir_spinbox.pack(side=tk.LEFT, padx=2)
        self.dir_spinbox.bind("<MouseWheel>", lambda e: "break")
        ttk.Button(dir_frame, text="Set", command=lambda: self.send_quick_command(0x01, self.dir_var.get()),
                   width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(dir_frame, text="Get", command=lambda: self.send_query_command(0x01),
                   width=6).pack(side=tk.LEFT, padx=2)

        # 速度设置
        speed_frame = ttk.Frame(quick_frame)
        speed_frame.pack(fill=tk.X, pady=5)

        ttk.Label(speed_frame, text="Speed(1-800):").pack(side=tk.LEFT, padx=2)
        self.speed_var = tk.IntVar(value=100)
        self.speed_spinbox = ttk.Spinbox(speed_frame, from_=1, to=800, textvariable=self.speed_var,
                    width=8)
        self.speed_spinbox.pack(side=tk.LEFT, padx=2)
        self.speed_spinbox.bind("<MouseWheel>", lambda e: "break")
        ttk.Button(speed_frame, text="Set", command=self.set_speed,
                   width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(speed_frame, text="Get", command=lambda: self.send_query_command(0x04),
                   width=6).pack(side=tk.LEFT, padx=2)

        # 行程设置
        travel_frame = ttk.LabelFrame(quick_frame, text="Travel Setting", padding=5)
        travel_frame.pack(fill=tk.X, pady=5)

        # 圈数
        ttk.Label(travel_frame, text="Revolutions:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.rev_var = tk.IntVar(value=0)
        self.rev_spinbox = ttk.Spinbox(travel_frame, from_=0, to=65535, textvariable=self.rev_var,
                    width=10)
        self.rev_spinbox.grid(row=0, column=1, padx=2)
        self.rev_spinbox.bind("<MouseWheel>", lambda e: "break")
        ttk.Button(travel_frame, text="Set", command=lambda: self.send_quick_command(0x06, self.rev_var.get()),
                   width=6).grid(row=0, column=2, padx=2)
        ttk.Button(travel_frame, text="Get", command=lambda: self.send_query_command(0x06),
                   width=6).grid(row=0, column=3, padx=2)

        # 角度
        ttk.Label(travel_frame, text="Angle(0-360):").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        self.angle_var = tk.IntVar(value=0)
        self.angle_spinbox = ttk.Spinbox(travel_frame, from_=0, to=360, textvariable=self.angle_var,
                    width=10)
        self.angle_spinbox.grid(row=1, column=1, padx=2, pady=2)
        self.angle_spinbox.bind("<MouseWheel>", lambda e: "break")
        ttk.Button(travel_frame, text="Set", command=self.set_angle,
                   width=6).grid(row=1, column=2, padx=2, pady=2)
        ttk.Button(travel_frame, text="Get", command=lambda: self.send_query_command(0x07),
                   width=6).grid(row=1, column=3, padx=2, pady=2)

        # 脉冲
        ttk.Label(travel_frame, text="Pulse(0-65535):").grid(row=2, column=0, sticky=tk.W, padx=2)
        self.pulse_var = tk.IntVar(value=0)
        self.pulse_spinbox = ttk.Spinbox(travel_frame, from_=0, to=65535, textvariable=self.pulse_var,
                    width=10)
        self.pulse_spinbox.grid(row=2, column=1, padx=2)
        self.pulse_spinbox.bind("<MouseWheel>", lambda e: "break")
        ttk.Button(travel_frame, text="Set", command=lambda: self.send_quick_command(0x05, self.pulse_var.get()),
                   width=6).grid(row=2, column=2, padx=2)
        ttk.Button(travel_frame, text="Get", command=lambda: self.send_query_command(0x05),
                   width=6).grid(row=2, column=3, padx=2)

        # 高级功能
        adv_frame = ttk.LabelFrame(quick_frame, text="Advanced", padding=5)
        adv_frame.pack(fill=tk.X, pady=5)

        # 配置列权重，使第1列可以扩展
        adv_frame.columnconfigure(1, weight=1)

        # 脱机/锁定 (0=锁定, 1=脱机使能)
        ttk.Label(adv_frame, text="Enable(0=Lock,1=Free):").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.enable_var = tk.IntVar(value=0)
        self.enable_spinbox = ttk.Spinbox(adv_frame, from_=0, to=1, textvariable=self.enable_var,
                    width=8)
        self.enable_spinbox.grid(row=0, column=1, padx=2)
        self.enable_spinbox.bind("<MouseWheel>", lambda e: "break")
        ttk.Button(adv_frame, text="Set", command=lambda: self.send_quick_command(0x09, self.enable_var.get()),
                   width=6).grid(row=0, column=2, padx=2)
        ttk.Button(adv_frame, text="Get", command=lambda: self.send_query_command(0x09),
                   width=6).grid(row=0, column=3, padx=2)

        # 加减速系数
        ttk.Label(adv_frame, text="Accel(0-10):").grid(row=1, column=0, sticky=tk.W, padx=2)
        self.accel_var = tk.IntVar(value=5)
        self.accel_spinbox = ttk.Spinbox(adv_frame, from_=0, to=10, textvariable=self.accel_var,
                    width=8)
        self.accel_spinbox.grid(row=1, column=1, padx=2)
        self.accel_spinbox.bind("<MouseWheel>", lambda e: "break")
        ttk.Button(adv_frame, text="Set", command=lambda: self.send_quick_command(0x0E, self.accel_var.get()),
                   width=6).grid(row=1, column=2, padx=2)
        ttk.Button(adv_frame, text="Get", command=lambda: self.send_query_command(0x0E),
                   width=6).grid(row=1, column=3, padx=2)

    def create_manual_command(self, parent):
        """创建手动指令输入区域"""
        manual_frame = ttk.LabelFrame(parent, text="Manual Command (HEX)", padding=10)
        manual_frame.pack(fill=tk.X, pady=5)

        # 指令输入
        ttk.Label(manual_frame, text="Command:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.cmd_var = tk.StringVar()
        ttk.Entry(manual_frame, textvariable=self.cmd_var, width=30).grid(row=0, column=1, columnspan=2, padx=2, sticky=tk.EW)

        # 示例按钮
        ttk.Button(manual_frame, text="Ex: Run", command=lambda: self.set_manual_cmd("01 06 00 02 00 01"),
                   width=8).grid(row=1, column=0, padx=2, pady=5)
        ttk.Button(manual_frame, text="Ex: Stop", command=lambda: self.set_manual_cmd("01 06 00 03 00 01"),
                   width=8).grid(row=1, column=1, padx=2, pady=5)
        ttk.Button(manual_frame, text="Ex: Query", command=lambda: self.set_manual_cmd("01 03 00 04 00 01"),
                   width=8).grid(row=1, column=2, padx=2, pady=5)

        # 发送按钮
        ttk.Button(manual_frame, text="Send Manual Command", command=self.send_manual_command,
                   width=25).grid(row=2, column=0, columnspan=3, pady=5)

        manual_frame.columnconfigure(1, weight=1)

    def create_log_area(self, parent):
        """创建日志显示区域"""
        log_frame = ttk.LabelFrame(parent, text="Communication Log", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)

        # 工具栏
        toolbar = ttk.Frame(log_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(toolbar, text="Clear Log", command=self.clear_log).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="Copy Selected", command=self.copy_selected).pack(side=tk.RIGHT, padx=5)

        # 显示选项
        self.show_hex_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Show HEX", variable=self.show_hex_var).pack(side=tk.LEFT, padx=5)
        self.show_ascii_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(toolbar, text="Show ASCII", variable=self.show_ascii_var).pack(side=tk.LEFT, padx=5)

        # 日志文本框
        self.log_area = scrolledtext.ScrolledText(log_frame, state='disabled', height=20,
                                                   font=("Consolas", 10))
        self.log_area.pack(fill=tk.BOTH, expand=True)

        self.log_area.tag_config("sent", foreground="blue")
        self.log_area.tag_config("received", foreground="green")
        self.log_area.tag_config("error", foreground="red")
        self.log_area.tag_config("info", foreground="gray")

    def refresh_ports(self, event=None, initial=False):
        """
        刷新可用串口列表

        :param event: tkinter 事件对象
        :param initial: 是否为初始化调用，初始时不自动选择第一个端口
        """
        ports = sorted([port.device for port in serial.tools.list_ports.comports()])
        self.port_combo['values'] = ports if ports else []

        if initial:
            # 初始化时清空选择，等待用户手动选择
            self.port_var.set('')
        elif not self.port_var.get() and ports:
            # 非初始化时，如果没有选中端口，则选择第一个
            self.port_combo.set(ports[0])

    def toggle_port(self):
        """打开或关闭串口"""
        if self.is_open:
            self.close_port()
        else:
            self.open_port()

    def open_port(self):
        """打开串口连接"""
        port = self.port_var.get()
        if not port:
            self.add_log("Error: No port selected", "error")
            return

        try:
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
                timeout=0.5
            )

            self.is_open = True
            self.btn_open.config(text="Close Port")
            self.add_log(f"Port {port} opened successfully", "info")
            self.log(f"Motor Debug: Port {port} opened", "SER")

        except Exception as e:
            self.add_log(f"Error opening port: {e}", "error")
            self.serial_conn = None

    def close_port(self):
        """关闭串口连接"""
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception as e:
                self.add_log(f"Error closing port: {e}", "error")

        self.serial_conn = None
        self.is_open = False
        self.btn_open.config(text="Open Port")
        self.add_log("Port closed", "info")
        self.log("Motor Debug: Port closed", "SER")

    def calculate_crc(self, data):
        """计算 Modbus CRC16 校验码"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def send_quick_command(self, register, value):
        """发送快速设置指令 (功能码 06)"""
        if not self.is_open or not self.serial_conn:
            self.add_log("Error: Port not open", "error")
            return

        try:
            data = struct.pack('>BBHH', self.device_addr, 0x06, register, value)
            crc = self.calculate_crc(data)
            crc_low = crc & 0xFF
            crc_high = (crc >> 8) & 0xFF
            command = data + bytes([crc_low, crc_high])

            self.send_and_receive(command)

        except Exception as e:
            self.add_log(f"Error sending command: {e}", "error")

    def send_query_command(self, register):
        """
        发送查询指令 (功能码 03)

        :param register: 寄存器地址
        """
        if not self.is_open or not self.serial_conn:
            self.add_log("Error: Port not open", "error")
            return

        try:
            data = struct.pack('>BBHH', self.device_addr, 0x03, register, 1)
            crc = self.calculate_crc(data)
            crc_low = crc & 0xFF
            crc_high = (crc >> 8) & 0xFF
            command = data + bytes([crc_low, crc_high])

            # 保存当前查询的寄存器地址，用于响应处理
            self.pending_query_register = register
            self.send_and_receive(command)

        except Exception as e:
            self.add_log(f"Error sending query: {e}", "error")

    def get_all_parameters(self):
        """
        获取所有电机参数并更新到输入框
        依次查询：方向、速度、脉冲、圈数、角度、加减速系数、脱机使能
        """
        if not self.is_open or not self.serial_conn:
            self.add_log("Error: Port not open", "error")
            return

        self.add_log("Starting to get all parameters...", "info")

        # 定义要查询的寄存器列表
        registers = [
            (0x01, "Direction"),
            (0x04, "Speed"),
            (0x05, "Pulse"),
            (0x06, "Revolutions"),
            (0x07, "Angle"),
            (0x0E, "Acceleration"),
            (0x09, "Enable Status"),
            (0x02, "Run Status")
        ]

        # 使用索引来跟踪当前查询的寄存器
        self._get_all_registers = registers
        self._get_all_index = 0

        # 开始依次查询
        self._query_next_register()

    def _query_next_register(self):
        """查询下一个寄存器"""
        if not hasattr(self, '_get_all_registers') or not hasattr(self, '_get_all_index'):
            return

        if self._get_all_index >= len(self._get_all_registers):
            # 所有寄存器查询完成
            self.add_log("All parameters retrieved successfully!", "info")
            delattr(self, '_get_all_registers')
            delattr(self, '_get_all_index')
            return

        register, name = self._get_all_registers[self._get_all_index]

        # 发送查询命令
        try:
            data = struct.pack('>BBHH', self.device_addr, 0x03, register, 1)
            crc = self.calculate_crc(data)
            crc_low = crc & 0xFF
            crc_high = (crc >> 8) & 0xFF
            command = data + bytes([crc_low, crc_high])

            # 标记这是批量查询的一部分
            self._is_batch_query = True
            self.pending_query_register = register

            # 清空接收缓冲区
            self.serial_conn.reset_input_buffer()

            # 发送指令
            self.serial_conn.write(command)

            # 显示发送的数据
            hex_str = ' '.join(f'{b:02X}' for b in command)
            self.add_log(f"[TX] {hex_str} (Get {name})", "sent")

            # 等待响应
            self.after(150, lambda: self._read_batch_response())

        except Exception as e:
            self.add_log(f"Error querying {name}: {e}", "error")
            self._get_all_index += 1
            self.after(100, self._query_next_register)

    def _read_batch_response(self):
        """读取批量查询的响应"""
        if not self.serial_conn or not self.serial_conn.is_open:
            self._get_all_index += 1
            self.after(100, self._query_next_register)
            return

        try:
            if self.serial_conn.in_waiting > 0:
                response = self.serial_conn.read(self.serial_conn.in_waiting)

                # 显示接收的数据
                hex_str = ' '.join(f'{b:02X}' for b in response)
                display_str = f"[RX] {hex_str}"

                # 解析响应并更新输入框
                data_value = None
                if len(response) >= 5:
                    if response[1] & 0x80:
                        display_str += "  [ERROR RESPONSE]"
                    elif response[1] == 0x03 and len(response) >= 5:
                        byte_count = response[2]
                        if len(response) >= 3 + byte_count + 2:
                            data_value = int.from_bytes(response[3:3+byte_count], 'big')
                            display_str += f"  [Value: {data_value}]"
                            # 更新输入框
                            self.update_input_value(data_value)

                self.add_log(display_str, "received")
            else:
                self.add_log("[RX] No response (timeout)", "info")

        except Exception as e:
            self.add_log(f"Error reading response: {e}", "error")

        # 查询下一个寄存器
        self._get_all_index += 1
        self.after(100, self._query_next_register)

    def set_speed(self):
        """设置速度"""
        speed = self.speed_var.get()
        if 1 <= speed <= 800:
            self.send_quick_command(0x04, speed)
        else:
            self.add_log("Error: Speed must be 1-800", "error")

    def set_angle(self):
        """设置角度 (转换为脉冲: 1圈=360度=1600脉冲)"""
        angle = self.angle_var.get()
        if 0 <= angle <= 360:
            pulse = int(angle * 1600 / 360)
            self.send_quick_command(0x07, pulse)
        else:
            self.add_log("Error: Angle must be 0-360", "error")

    def set_manual_cmd(self, cmd_str):
        """设置手动指令示例"""
        self.cmd_var.set(cmd_str)

    def send_manual_command(self):
        """发送手动输入的指令"""
        if not self.is_open or not self.serial_conn:
            self.add_log("Error: Port not open", "error")
            return

        cmd_str = self.cmd_var.get().strip()
        if not cmd_str:
            self.add_log("Error: Empty command", "error")
            return

        try:
            # 解析十六进制字符串
            hex_bytes = cmd_str.replace(' ', '').replace('0x', '').replace(',', '')
            if len(hex_bytes) % 2 != 0:
                hex_bytes = '0' + hex_bytes

            command = bytes.fromhex(hex_bytes)

            # 如果指令长度不足6字节，添加CRC
            if len(command) == 6:
                crc = self.calculate_crc(command)
                crc_low = crc & 0xFF
                crc_high = (crc >> 8) & 0xFF
                command = command + bytes([crc_low, crc_high])
                self.add_log(f"Auto-added CRC: {crc_low:02X} {crc_high:02X}", "info")

            self.send_and_receive(command)

        except ValueError as e:
            self.add_log(f"Error: Invalid hex format - {e}", "error")
        except Exception as e:
            self.add_log(f"Error sending manual command: {e}", "error")

    def send_and_receive(self, command):
        """发送指令并接收响应"""
        try:
            # 清空接收缓冲区
            self.serial_conn.reset_input_buffer()

            # 发送指令
            self.serial_conn.write(command)

            # 显示发送的数据
            hex_str = ' '.join(f'{b:02X}' for b in command)
            display_str = f"[TX] {hex_str}"
            if self.show_ascii_var.get():
                ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in command)
                display_str += f"  |  {ascii_str}"
            self.add_log(display_str, "sent")

            # 等待并接收响应
            self.after(100, lambda: self.read_response())

        except Exception as e:
            self.add_log(f"Error in communication: {e}", "error")

    def read_response(self):
        """读取串口响应"""
        if not self.serial_conn or not self.serial_conn.is_open:
            return

        try:
            # 检查是否有数据可读
            if self.serial_conn.in_waiting > 0:
                response = self.serial_conn.read(self.serial_conn.in_waiting)

                # 显示接收的数据
                hex_str = ' '.join(f'{b:02X}' for b in response)
                display_str = f"[RX] {hex_str}"

                # 解析响应
                data_value = None
                if len(response) >= 5:
                    if response[1] & 0x80:
                        display_str += "  [ERROR RESPONSE]"
                    elif response[1] == 0x03 and len(response) >= 5:
                        byte_count = response[2]
                        if len(response) >= 3 + byte_count + 2:
                            data_value = int.from_bytes(response[3:3+byte_count], 'big')
                            display_str += f"  [Value: {data_value}]"

                            # 更新对应输入框的值
                            self.update_input_value(data_value)

                if self.show_ascii_var.get():
                    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in response)
                    display_str += f"  |  {ascii_str}"

                self.add_log(display_str, "received")

                # 清除待处理的查询寄存器
                if hasattr(self, 'pending_query_register'):
                    delattr(self, 'pending_query_register')
            else:
                # 再等待一下，有些设备响应较慢
                self.after(100, lambda: self.read_delayed())

        except Exception as e:
            self.add_log(f"Error reading response: {e}", "error")

    def read_delayed(self):
        """延迟读取响应"""
        if not self.serial_conn or not self.serial_conn.is_open:
            return

        try:
            if self.serial_conn.in_waiting > 0:
                response = self.serial_conn.read(self.serial_conn.in_waiting)
                hex_str = ' '.join(f'{b:02X}' for b in response)
                display_str = f"[RX] {hex_str}"

                if response[1] & 0x80:
                    display_str += "  [ERROR RESPONSE]"

                if self.show_ascii_var.get():
                    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in response)
                    display_str += f"  |  {ascii_str}"

                self.add_log(display_str, "received")
            else:
                self.add_log("[RX] No response (timeout)", "info")

        except Exception as e:
            self.add_log(f"Error reading delayed response: {e}", "error")

    def update_input_value(self, value):
        """
        根据查询的寄存器地址，更新对应的输入框值

        :param value: 从设备读取到的值
        """
        if not hasattr(self, 'pending_query_register'):
            return

        register = self.pending_query_register

        # 根据寄存器地址更新对应的变量
        if register == 0x01:  # 方向
            self.dir_var.set(value)
            self.add_log(f"  -> Direction updated to: {value} ({'CW' if value == 1 else 'CCW'})", "info")
        elif register == 0x04:  # 速度
            self.speed_var.set(value)
            self.add_log(f"  -> Speed updated to: {value}", "info")
        elif register == 0x05:  # 脉冲
            self.pulse_var.set(value)
            self.add_log(f"  -> Pulse updated to: {value}", "info")
        elif register == 0x06:  # 圈数
            self.rev_var.set(value)
            self.add_log(f"  -> Revolutions updated to: {value}", "info")
        elif register == 0x07:  # 角度
            # 将脉冲转换为角度显示 (1圈=360度=1600脉冲)
            angle = int(value * 360 / 1600)
            self.angle_var.set(angle)
            self.add_log(f"  -> Angle updated to: {angle}° (pulse: {value})", "info")
        elif register == 0x0E:  # 加减速系数
            self.accel_var.set(value)
            self.add_log(f"  -> Acceleration coefficient updated to: {value}", "info")
        elif register == 0x02:  # 运行状态
            status_str = "Running" if value == 1 else "Stopped"
            self.add_log(f"  -> Run status: {status_str} ({value})", "info")
        elif register == 0x09:  # 脱机使能
            self.enable_var.set(value)
            status_str = "Free (脱机)" if value == 1 else "Lock (锁定)"
            self.add_log(f"  -> Enable status updated to: {value} ({status_str})", "info")

    def add_log(self, message, tag="info"):
        """添加日志到显示区域"""
        timestamp = self.get_timestamp()
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def get_timestamp(self):
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]

    def clear_log(self):
        """清空日志"""
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state='disabled')

    def copy_selected(self):
        """复制选中的内容到剪贴板"""
        try:
            selected = self.log_area.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.clipboard_clear()
            self.clipboard_append(selected)
        except tk.TclError:
            pass
