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

        self.create_widgets()
        self.bind_keys()

    def create_widgets(self):
        """
        创建运动控制界面的所有子组件，主要是十字型布局的方向控制按钮。
        """
        self.control_container = ttk.Frame(self)
        self.control_container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

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
        """
        axis_name, serial_key, _ = self.get_axis_info(direction)
        if axis_name is None:
            self.log(f"Button pressed: {direction} (Unknown axis)", "MOT")
            return

        # 如果已经在按下状态（键盘自动重复），则忽略
        if self.is_pressing.get(direction, False):
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
        """
        axis_name, serial_key, _ = self.get_axis_info(direction)
        if axis_name is None:
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
