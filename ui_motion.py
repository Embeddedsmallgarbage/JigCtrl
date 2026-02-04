import tkinter as tk
from tkinter import ttk
import struct
import threading
import time


class MotionControlFrame(ttk.Frame):
    """
    MotionControlFrame 类：运动控制界面类，继承自 ttk.Frame。
    提供方向键控制按钮以及键盘快捷键绑定功能，用于控制电机的运动。
    支持点按（转一圈）和长按（持续转动）两种模式。
    X轴使用左右方向键控制，Y轴使用上下方向键控制。
    """

    def __init__(self, master=None, settings_source=None, log_callback=None):
        super().__init__(master)
        self.settings_source = settings_source
        self.log = log_callback if log_callback else print

        self.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.device_addr = 0x01
        self.long_press_threshold = 300

        self.press_start_time = {}
        self.is_long_press = {}
        self.is_pressing = {}
        self.press_timer = {}

        # 脉冲数显示变量
        self.x_pulse_var = tk.StringVar(value="--")
        self.y_pulse_var = tk.StringVar(value="--")

        self.create_widgets()
        self.bind_keys()

    def create_widgets(self):
        """
        创建运动控制界面的所有子组件。
        包含按键控制区域和坐标系构建区域。
        """
        # --- 按键控制区域 (Button Control Area) ---
        self.control_frame = ttk.LabelFrame(self, text="Button Control", padding=10)
        self.control_frame.pack(anchor=tk.NW, padx=10, pady=10)

        # 方向按钮容器
        self.control_container = ttk.Frame(self.control_frame)
        self.control_container.pack(expand=True)

        # --- 坐标系构建区域 (Coordinate System Area) ---
        self.coord_frame = ttk.LabelFrame(self, text="Coordinate System", padding=10)
        self.coord_frame.pack(anchor=tk.NW, padx=10, pady=10, fill=tk.X)

        # 设置原点按钮和回到原点按钮区域
        origin_button_frame = ttk.Frame(self.coord_frame)
        origin_button_frame.pack(anchor=tk.W, padx=5, pady=5, fill=tk.X)

        # 设置原点按钮
        self.btn_set_origin = ttk.Button(
            origin_button_frame,
            text="Set Origin",
            command=self.on_set_origin
        )
        self.btn_set_origin.pack(side=tk.LEFT, padx=(0, 5))

        # 回到原点按钮
        self.btn_return_origin = ttk.Button(
            origin_button_frame,
            text="Return to Origin",
            command=self.on_return_to_origin
        )
        self.btn_return_origin.pack(side=tk.LEFT, padx=(0, 20))

        # 回原点速度控制区域
        ttk.Label(origin_button_frame, text="Homing Speed:").pack(side=tk.LEFT, padx=(0, 5))
        
        # 回原点速度输入框
        self.homing_speed_var = tk.StringVar(value="100")
        self.entry_homing_speed = ttk.Entry(origin_button_frame, textvariable=self.homing_speed_var, width=8)
        self.entry_homing_speed.pack(side=tk.LEFT, padx=(0, 5))
        
        # 获取回原点速度按钮
        self.btn_get_homing_speed = ttk.Button(
            origin_button_frame,
            text="Get",
            command=self.on_get_homing_speed,
            width=6
        )
        self.btn_get_homing_speed.pack(side=tk.LEFT, padx=(0, 5))
        
        # 设置回原点速度按钮
        self.btn_set_homing_speed = ttk.Button(
            origin_button_frame,
            text="Set",
            command=self.on_set_homing_speed,
            width=6
        )
        self.btn_set_homing_speed.pack(side=tk.LEFT)

        # 获取脉冲数按钮和显示区域
        pulse_frame = ttk.Frame(self.coord_frame)
        pulse_frame.pack(anchor=tk.W, padx=5, pady=5, fill=tk.X)

        # 左侧：按钮区域
        button_frame = ttk.Frame(pulse_frame)
        button_frame.pack(side=tk.LEFT)

        # 获取X轴脉冲数按钮
        self.btn_get_x_pulse = ttk.Button(
            button_frame,
            text="Get X-Axis Pulse",
            command=lambda: self.on_get_pulse("X-Axis", "X-Axis Motor")
        )
        self.btn_get_x_pulse.pack(side=tk.LEFT, padx=(0, 5))

        # 获取Y轴脉冲数按钮
        self.btn_get_y_pulse = ttk.Button(
            button_frame,
            text="Get Y-Axis Pulse",
            command=lambda: self.on_get_pulse("Y-Axis", "Y-Axis Motor")
        )
        self.btn_get_y_pulse.pack(side=tk.LEFT)

        # 右侧：脉冲数显示区域
        display_frame = ttk.Frame(pulse_frame)
        display_frame.pack(side=tk.LEFT, padx=(20, 0))

        # X轴脉冲数显示
        ttk.Label(display_frame, text="X-Axis Pulse:").pack(side=tk.LEFT, padx=(0, 5))
        self.lbl_x_pulse = ttk.Label(display_frame, textvariable=self.x_pulse_var, font=("Cambria", 10, "bold"), foreground="blue")
        self.lbl_x_pulse.pack(side=tk.LEFT, padx=(0, 20))

        # Y轴脉冲数显示
        ttk.Label(display_frame, text="Y-Axis Pulse:").pack(side=tk.LEFT, padx=(0, 5))
        self.lbl_y_pulse = ttk.Label(display_frame, textvariable=self.y_pulse_var, font=("Cambria", 10, "bold"), foreground="blue")
        self.lbl_y_pulse.pack(side=tk.LEFT)

        style = ttk.Style()
        style.configure("Dir.TButton", font=("Arial", 12, "bold"), width=8)

        self.btn_up = ttk.Button(self.control_container, text="↑(Up)", style="Dir.TButton")
        self.btn_left = ttk.Button(self.control_container, text="←(Left)", style="Dir.TButton")
        self.btn_down = ttk.Button(self.control_container, text="↓(Down)", style="Dir.TButton")
        self.btn_right = ttk.Button(self.control_container, text="→(Right)", style="Dir.TButton")

        self.btn_up.grid(row=0, column=1, padx=5, pady=5)
        self.btn_left.grid(row=1, column=0, padx=5, pady=5)
        self.btn_down.grid(row=1, column=1, padx=5, pady=5)
        self.btn_right.grid(row=1, column=2, padx=5, pady=5)

        self.buttons = {
            'Up': self.btn_up,
            'Down': self.btn_down,
            'Left': self.btn_left,
            'Right': self.btn_right
        }

        for direction, btn in self.buttons.items():
            btn.bind('<ButtonPress-1>', lambda e, d=direction: self.on_press(d))
            btn.bind('<ButtonRelease-1>', lambda e, d=direction: self.on_release(d))

    def bind_keys(self):
        """
        绑定页面可见性相关的事件，确保快捷键仅在该页签可见时生效。
        """
        self.bind('<Visibility>', self.on_visibility)
        self.bind('<Unmap>', self.on_unmap)

    def on_visibility(self, event):
        """
        当运动控制页签被激活/可见时，启用全局键盘绑定。
        """
        top = self.winfo_toplevel()

        self.bind_id_press_up = top.bind('<KeyPress-Up>', lambda e: self.on_press('Up'))
        self.bind_id_release_up = top.bind('<KeyRelease-Up>', lambda e: self.on_release('Up'))
        self.bind_id_press_down = top.bind('<KeyPress-Down>', lambda e: self.on_press('Down'))
        self.bind_id_release_down = top.bind('<KeyRelease-Down>', lambda e: self.on_release('Down'))
        self.bind_id_press_left = top.bind('<KeyPress-Left>', lambda e: self.on_press('Left'))
        self.bind_id_release_left = top.bind('<KeyRelease-Left>', lambda e: self.on_release('Left'))
        self.bind_id_press_right = top.bind('<KeyPress-Right>', lambda e: self.on_press('Right'))
        self.bind_id_release_right = top.bind('<KeyRelease-Right>', lambda e: self.on_release('Right'))

        self.focus_set()

    def on_unmap(self, event):
        """
        当切换到其他页签时，解除键盘绑定，防止误触发电机运动。
        """
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
        except (tk.TclError, AttributeError):
            pass

    def get_axis_info(self, direction):
        """
        根据方向获取轴信息。

        :param direction: 方向字符串 ('Up', 'Down', 'Left', 'Right')
        :return: (axis_name, serial_key, direction_value) 元组
        """
        if direction in ['Up', 'Down']:
            axis_name = "Y-Axis"
            serial_key = "Y-Axis Motor"
            direction_value = 1 if direction == 'Up' else 0
        elif direction in ['Left', 'Right']:
            axis_name = "X-Axis"
            serial_key = "X-Axis Motor"
            direction_value = 1 if direction == 'Left' else 0
        else:
            return None, None, None
        return axis_name, serial_key, direction_value

    def on_press(self, direction):
        """
        处理按钮/键盘按下事件。
        启动定时器检测是否为长按。
        在发送命令前先查询电机是否正在运行，如果正在运行则忽略此次按键。
        """
        axis_name, serial_key, _ = self.get_axis_info(direction)
        if axis_name is None:
            self.log(f"Button pressed: {direction} (Unknown axis)", "MOT")
            return

        # 如果已经在按下状态（键盘自动重复），则忽略
        if self.is_pressing.get(direction, False):
            return

        # 先检查电机是否正在运行
        serial_conn = self.get_serial_connection(serial_key)
        if serial_conn:
            if self.is_motor_running(serial_conn, serial_key):
                self.log(f"Button pressed: {direction} ({axis_name}) - Ignored, motor is already running", "MOT")
                # 标记此次按键被忽略，这样 release 不会执行操作
                self.is_pressing[direction] = False
                self.is_long_press[direction] = False
                return
        else:
            self.log(f"Button pressed: {direction} ({axis_name}) - {serial_key} not connected", "ERR")
            return

        self.is_pressing[direction] = True
        self.is_long_press[direction] = False
        self.press_start_time[direction] = time.time() * 1000

        btn = self.buttons.get(direction)
        if btn:
            btn.state(['pressed'])

        self.press_timer[direction] = self.after(self.long_press_threshold,
                                                  lambda: self.on_long_press_detected(direction))

        self.log(f"Button pressed: {direction} ({axis_name})", "MOT")

    def on_long_press_detected(self, direction):
        """
        长按检测定时器回调。
        如果超过阈值仍然按着，则判定为长按，开始持续转动。
        """
        if self.is_pressing.get(direction, False):
            self.is_long_press[direction] = True
            axis_name, _, _ = self.get_axis_info(direction)
            self.log(f"Long press detected: {direction} ({axis_name}), starting continuous motion", "MOT")
            self.start_continuous_motion(direction)

    def on_release(self, direction):
        """
        处理按钮/键盘释放事件。
        根据是点按还是长按执行不同的操作。
        如果 press 被忽略（is_pressing 为 False），则 release 也不执行操作。
        """
        axis_name, serial_key, _ = self.get_axis_info(direction)
        if axis_name is None:
            return

        # 如果 press 被忽略（电机正在运行或串口未连接），则 release 也不执行操作
        if not self.is_pressing.get(direction, False):
            btn = self.buttons.get(direction)
            if btn:
                btn.state(['!pressed'])
            return

        self.is_pressing[direction] = False

        if direction in self.press_timer:
            self.after_cancel(self.press_timer[direction])
            del self.press_timer[direction]

        btn = self.buttons.get(direction)
        if btn:
            btn.state(['!pressed'])

        if self.is_long_press.get(direction, False):
            self.log(f"Button released: {direction} ({axis_name}), stopping continuous motion", "MOT")
            self.stop_motion(direction)
        else:
            self.log(f"Button released: {direction} ({axis_name}), executing single step", "MOT")
            self.execute_single_step(direction)

        self.is_long_press[direction] = False

    def on_set_origin(self):
        """
        设置原点按钮回调函数。
        向 X 轴和 Y 轴电机发送设置原点命令（寄存器 0x15）。
        """
        axes = [
            ("X-Axis", "X-Axis Motor"),
            ("Y-Axis", "Y-Axis Motor")
        ]

        for axis_name, serial_key in axes:
            serial_conn = self.get_serial_connection(serial_key)
            if serial_conn:
                # 发送设置原点命令 (寄存器 0x15, 值 0x01)
                if self.send_command_and_wait_response(serial_conn, serial_key, 0x15, 0x01):
                    self.log(f"Origin set successfully for {axis_name}", "MOT")
                else:
                    self.log(f"Failed to set origin for {axis_name}", "ERR")
            else:
                self.log(f"Error: {serial_key} serial port not open", "ERR")

    def on_return_to_origin(self):
        """
        回到原点按钮回调函数。
        向 X 轴和 Y 轴电机发送回到原点命令（寄存器 0x0A）。
        """
        axes = [
            ("X-Axis", "X-Axis Motor"),
            ("Y-Axis", "Y-Axis Motor")
        ]

        for axis_name, serial_key in axes:
            serial_conn = self.get_serial_connection(serial_key)
            if serial_conn:
                # 发送回到原点命令 (寄存器 0x0A, 值 0x01)
                if self.send_command_and_wait_response(serial_conn, serial_key, 0x0A, 0x01):
                    self.log(f"Return to origin command sent successfully for {axis_name}", "MOT")
                else:
                    self.log(f"Failed to send return to origin command for {axis_name}", "ERR")
            else:
                self.log(f"Error: {serial_key} serial port not open", "ERR")

    def on_get_homing_speed(self):
        """
        获取回原点速度按钮回调函数。
        读取寄存器 0x1A，返回 2 字节速度数据。
        """
        # 优先读取 X 轴的回原点速度
        serial_key = "X-Axis Motor"
        axis_name = "X-Axis"
        
        serial_conn = self.get_serial_connection(serial_key)
        if not serial_conn:
            self.log(f"Error: {serial_key} serial port not open", "ERR")
            return

        try:
            port_info = self.get_serial_port_info(serial_conn, serial_key)

            # 清空接收缓冲区
            serial_conn.reset_input_buffer()

            # 构建读取命令 (功能码 0x03, 寄存器 0x1A, 读取 1 个寄存器 = 2 字节)
            data = struct.pack('>BBHH', self.device_addr, 0x03, 0x1A, 0x01)
            crc = self.calculate_crc(data)
            crc_low = crc & 0xFF
            crc_high = (crc >> 8) & 0xFF
            command = data + bytes([crc_low, crc_high])

            # 发送命令
            serial_conn.write(command)
            hex_str = ' '.join([f'{b:02X}' for b in command])
            self.log(f"{port_info} TX: [{hex_str}] Query Homing Speed", "MOT")

            # 等待接收回复（读命令回复通常是7字节：地址+功能码+字节数+2字节数据+2字节CRC）
            response = self.wait_for_response(serial_conn, expected_length=7, timeout=0.5)

            if response and len(response) >= 7:
                resp_hex = ' '.join([f'{b:02X}' for b in response])
                # 解析回复：第2字节是数据字节数(0x02)，第3-4字节是速度数据(2字节，大端模式)
                homing_speed = (response[3] << 8) | response[4]
                self.log(f"{port_info} RX: [{resp_hex}] Homing Speed = {homing_speed} RPM", "MOT")
                # 更新输入框显示
                self.homing_speed_var.set(str(homing_speed))
            else:
                self.log(f"{port_info} RX: [Timeout - No response received]", "ERR")

        except Exception as e:
            self.log(f"Error querying homing speed for {axis_name}: {e}", "ERR")

    def on_set_homing_speed(self):
        """
        设置回原点速度按钮回调函数。
        向 X 轴和 Y 轴电机发送设置回原点速度命令（寄存器 0x1A）。
        """
        try:
            # 获取输入的速度值
            speed_str = self.homing_speed_var.get()
            speed = int(speed_str)
            
            # 验证速度范围
            if speed < 1 or speed > 800:
                self.log(f"Error: Homing speed must be between 1 and 800 RPM", "ERR")
                return
            
            axes = [
                ("X-Axis", "X-Axis Motor"),
                ("Y-Axis", "Y-Axis Motor")
            ]

            for axis_name, serial_key in axes:
                serial_conn = self.get_serial_connection(serial_key)
                if serial_conn:
                    # 发送设置回原点速度命令 (寄存器 0x1A, 值为速度)
                    if self.send_command_and_wait_response(serial_conn, serial_key, 0x1A, speed):
                        self.log(f"Homing speed set to {speed} RPM for {axis_name}", "MOT")
                    else:
                        self.log(f"Failed to set homing speed for {axis_name}", "ERR")
                else:
                    self.log(f"Error: {serial_key} serial port not open", "ERR")

        except ValueError:
            self.log(f"Error: Invalid homing speed value '{self.homing_speed_var.get()}'", "ERR")
        except Exception as e:
            self.log(f"Error setting homing speed: {e}", "ERR")

    def on_get_pulse(self, axis_name, serial_key):
        """
        获取指定轴的运行脉冲数按钮回调函数。
        读取寄存器 0x18，返回 4 字节脉冲数据。

        :param axis_name: 轴名称 ("X-Axis" 或 "Y-Axis")
        :param serial_key: 串口键名 ("X-Axis Motor" 或 "Y-Axis Motor")
        """
        serial_conn = self.get_serial_connection(serial_key)
        if not serial_conn:
            self.log(f"Error: {serial_key} serial port not open", "ERR")
            return

        try:
            port_info = self.get_serial_port_info(serial_conn, serial_key)

            # 清空接收缓冲区
            serial_conn.reset_input_buffer()

            # 构建读取命令 (功能码 0x03, 寄存器 0x18, 读取 2 个寄存器 = 4 字节)
            data = struct.pack('>BBHH', self.device_addr, 0x03, 0x18, 0x02)
            crc = self.calculate_crc(data)
            crc_low = crc & 0xFF
            crc_high = (crc >> 8) & 0xFF
            command = data + bytes([crc_low, crc_high])

            # 发送命令
            serial_conn.write(command)
            hex_str = ' '.join([f'{b:02X}' for b in command])
            self.log(f"{port_info} TX: [{hex_str}] Query Pulse Count", "MOT")

            # 等待接收回复（读命令回复通常是9字节：地址+功能码+字节数+4字节数据+2字节CRC）
            response = self.wait_for_response(serial_conn, expected_length=9, timeout=0.5)

            if response and len(response) >= 9:
                resp_hex = ' '.join([f'{b:02X}' for b in response])
                # 解析回复：第2字节是数据字节数(0x04)，第3-6字节是脉冲数据(4字节，大端模式，有符号)
                pulse_count_unsigned = (response[3] << 24) | (response[4] << 16) | (response[5] << 8) | response[6]
                # 将有符号数转换为Python整数（32位有符号）
                pulse_count = pulse_count_unsigned if pulse_count_unsigned < 0x80000000 else pulse_count_unsigned - 0x100000000
                self.log(f"{port_info} RX: [{resp_hex}] Pulse Count = {pulse_count}", "MOT")
                
                # 更新界面显示
                if axis_name == "X-Axis":
                    self.x_pulse_var.set(str(pulse_count))
                elif axis_name == "Y-Axis":
                    self.y_pulse_var.set(str(pulse_count))
            else:
                self.log(f"{port_info} RX: [Timeout - No response received]", "ERR")

        except Exception as e:
            self.log(f"Error querying pulse count for {axis_name}: {e}", "ERR")

    def execute_single_step(self, direction):
        """
        执行单步运动（点按）：设置方向，行程为1圈，然后运行。
        每条命令发送后等待回复才能发送下一条。
        """
        axis_name, serial_key, direction_value = self.get_axis_info(direction)
        if axis_name is None:
            return

        serial_conn = self.get_serial_connection(serial_key)
        if not serial_conn:
            self.log(f"Error: {serial_key} serial port not open", "ERR")
            return

        # 发送方向命令，等待回复
        if not self.send_command_and_wait_response(serial_conn, serial_key, 0x01, direction_value):
            self.log(f"Failed to set {axis_name} direction", "ERR")
            return

        # 发送行程命令（1圈），等待回复
        if not self.send_command_and_wait_response(serial_conn, serial_key, 0x06, 1):
            self.log(f"Failed to set {axis_name} revolutions", "ERR")
            return

        # 发送运行命令，等待回复
        if not self.send_command_and_wait_response(serial_conn, serial_key, 0x02, 1):
            self.log(f"Failed to start {axis_name} motion", "ERR")
            return

        self.log(f"Single step executed: {direction} ({axis_name}), revolutions=1", "MOT")

    def start_continuous_motion(self, direction):
        """
        开始持续转动（长按）：设置方向，行程为0（无限），然后运行。
        每条命令发送后等待回复才能发送下一条。
        """
        axis_name, serial_key, direction_value = self.get_axis_info(direction)
        if axis_name is None:
            return

        serial_conn = self.get_serial_connection(serial_key)
        if not serial_conn:
            self.log(f"Error: {serial_key} serial port not open", "ERR")
            return

        # 发送方向命令，等待回复
        if not self.send_command_and_wait_response(serial_conn, serial_key, 0x01, direction_value):
            self.log(f"Failed to set {axis_name} direction", "ERR")
            return

        # 发送行程命令（无限），等待回复
        if not self.send_command_and_wait_response(serial_conn, serial_key, 0x06, 0):
            self.log(f"Failed to set {axis_name} revolutions", "ERR")
            return

        # 发送运行命令，等待回复
        if not self.send_command_and_wait_response(serial_conn, serial_key, 0x02, 1):
            self.log(f"Failed to start {axis_name} motion", "ERR")
            return

        self.log(f"Continuous motion started: {direction} ({axis_name})", "MOT")

    def stop_motion(self, direction):
        """
        停止电机运动（发送停止命令）。
        发送后等待回复。
        """
        axis_name, serial_key, _ = self.get_axis_info(direction)
        if axis_name is None:
            return

        serial_conn = self.get_serial_connection(serial_key)
        if not serial_conn:
            self.log(f"Error: {serial_key} serial port not open", "ERR")
            return

        # 发送停止命令，等待回复
        if self.send_command_and_wait_response(serial_conn, serial_key, 0x03, 1):
            self.log(f"Motion stopped ({axis_name})", "MOT")
        else:
            self.log(f"Failed to stop {axis_name} motion", "ERR")

    def get_serial_connection(self, serial_key):
        """
        获取指定轴的串口连接。

        :param serial_key: 串口键名 ("X-Axis Motor" 或 "Y-Axis Motor")
        :return: 串口连接对象
        """
        if self.settings_source:
            return self.settings_source.get_serial_connection(serial_key)
        return None

    def is_motor_running(self, serial_conn, serial_key):
        """
        查询电机是否正在运行。
        通过读取寄存器 0x02 (运行/暂停状态) 来判断。

        :param serial_conn: 串口连接对象
        :param serial_key: 串口键名
        :return: True 如果电机正在运行，False 否则
        """
        try:
            port_info = self.get_serial_port_info(serial_conn, serial_key)

            # 清空接收缓冲区
            serial_conn.reset_input_buffer()

            # 构建读取命令 (功能码 0x03)
            data = struct.pack('>BBHH', self.device_addr, 0x03, 0x02, 0x01)
            crc = self.calculate_crc(data)
            crc_low = crc & 0xFF
            crc_high = (crc >> 8) & 0xFF
            command = data + bytes([crc_low, crc_high])

            # 发送命令
            serial_conn.write(command)
            hex_str = ' '.join([f'{b:02X}' for b in command])
            self.log(f"{port_info} TX: [{hex_str}] Query Run Status", "MOT")

            # 等待接收回复（读命令回复通常是7字节）
            response = self.wait_for_response(serial_conn, expected_length=7, timeout=0.5)

            if response and len(response) >= 7:
                resp_hex = ' '.join([f'{b:02X}' for b in response])
                self.log(f"{port_info} RX: [{resp_hex}]", "MOT")
                # 解析回复：第4个字节是数据高位，第5个字节是数据低位
                # 如果值为1，表示正在运行
                run_status = response[4] if len(response) > 4 else 0
                return run_status == 1
            else:
                self.log(f"{port_info} RX: [Timeout - No response received]", "ERR")
                return False

        except Exception as e:
            self.log(f"Error querying motor status: {e}", "ERR")
            return False

    def calculate_crc(self, data):
        """
        计算 Modbus CRC16 校验码。
        """
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def get_register_description(self, register, value):
        """
        获取寄存器命令的描述信息。

        :param register: 寄存器地址
        :param value: 写入值
        :return: 命令描述字符串
        """
        descriptions = {
            0x01: {0: "Direction: Reverse", 1: "Direction: Forward"},
            0x02: {0: "Pause", 1: "Run"},
            0x03: {1: "Stop"},
            0x04: None,  # 速度设置，动态显示
            0x05: None,  # 脉冲数，动态显示
            0x06: None,  # 圈数，动态显示
            0x07: None,  # 角度，动态显示
            0x09: {0: "Lock", 1: "Free"},
            0x0E: None,  # 加减速系数，动态显示
        }

        if register in descriptions:
            desc_map = descriptions[register]
            if desc_map is not None:
                return desc_map.get(value, f"Unknown value {value}")

        # 动态显示特定寄存器
        if register == 0x04:
            return f"Speed: {value} RPM"
        elif register == 0x05:
            return f"Pulse: {value}"
        elif register == 0x06:
            if value == 0:
                return "Revolutions: Infinite (Continuous)"
            return f"Revolutions: {value}"
        elif register == 0x07:
            return f"Angle: {value}°"
        elif register == 0x0E:
            return f"Accel Coefficient: {value}"

        return f"Register 0x{register:02X}, Value: {value}"

    def get_serial_port_info(self, serial_conn, serial_key):
        """
        获取串口连接的信息字符串。

        :param serial_conn: 串口连接对象
        :param serial_key: 串口键名
        :return: 串口信息字符串，如 "[X-Axis Motor: COM3]"
        """
        if serial_conn and serial_conn.is_open:
            port_name = serial_conn.port
            return f"[{serial_key}: {port_name}]"
        return f"[{serial_key}: Not Connected]"

    def send_command_and_wait_response(self, serial_conn, serial_key, register, value):
        """
        发送 Modbus-RTU 命令到电机控制器，并等待接收回复。
        只有在收到回复后才能发送下一个命令。

        :param serial_conn: 串口连接对象
        :param serial_key: 串口键名
        :param register: 寄存器地址
        :param value: 写入值
        :return: 是否成功发送并收到回复
        """
        try:
            # 获取串口信息
            port_info = self.get_serial_port_info(serial_conn, serial_key)

            # 清空接收缓冲区
            serial_conn.reset_input_buffer()

            # 构建命令
            data = struct.pack('>BBHH', self.device_addr, 0x06, register, value)
            crc = self.calculate_crc(data)
            crc_low = crc & 0xFF
            crc_high = (crc >> 8) & 0xFF
            command = data + bytes([crc_low, crc_high])

            # 发送命令
            serial_conn.write(command)
            hex_str = ' '.join([f'{b:02X}' for b in command])
            desc = self.get_register_description(register, value)
            self.log(f"{port_info} TX: [{hex_str}] {desc}", "MOT")

            # 等待接收回复（写命令回复通常是8字节）
            response = self.wait_for_response(serial_conn, expected_length=8, timeout=0.5)

            if response:
                resp_hex = ' '.join([f'{b:02X}' for b in response])
                self.log(f"{port_info} RX: [{resp_hex}]", "MOT")
                return True
            else:
                self.log(f"{port_info} RX: [Timeout - No response received]", "ERR")
                return False

        except Exception as e:
            self.log(f"Error sending command: {e}", "ERR")
            return False

    def wait_for_response(self, serial_conn, expected_length=8, timeout=0.5):
        """
        等待并读取串口回复数据。

        :param serial_conn: 串口连接对象
        :param expected_length: 期望接收的数据长度
        :param timeout: 超时时间（秒）
        :return: 接收到的字节数据，超时返回 None
        """
        original_timeout = serial_conn.timeout
        serial_conn.timeout = timeout

        try:
            response = bytearray()
            while len(response) < expected_length:
                chunk = serial_conn.read(expected_length - len(response))
                if not chunk:
                    break
                response.extend(chunk)

            return bytes(response) if len(response) > 0 else None
        finally:
            serial_conn.timeout = original_timeout
