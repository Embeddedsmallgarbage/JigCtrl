import tkinter as tk
from tkinter import ttk
import datetime
import time
import threading
import struct
from key_manager import KeyManager

class TestControlFrame(ttk.Frame):
    """
    TestControlFrame 类：负责测试流程的控制与监控。
    包含测试状态显示、启动/暂停/停止控制，以及核心测试循环逻辑。
    """
    def __init__(self, master=None, settings_source=None, log_callback=None):
        """
        初始化测试控制面板。
        
        :param master: 父容器组件
        :param settings_source: 设置信息来源（通常是 SettingsFrame 实例），用于获取测试参数和串口连接
        :param log_callback: 日志回调函数，用于输出测试过程中的信息
        """
        super().__init__(master)
        # --- 成员变量初始化 ---
        self.settings_source = settings_source
        self.log = log_callback if log_callback else print  # 如果未提供回调，则默认打印到控制台
        self.key_manager = KeyManager() # 初始化按键管理器
        self.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # --- 测试状态变量 ---
        self.timer_id = None            # Tkinter 定时器 ID，用于倒计时更新
        self.remaining_seconds = 0      # 剩余测试时间（秒）
        self.remaining_counts = 0       # 剩余测试次数
        self.current_item_index = 0     # 当前测试项索引
        self.test_flow = []             # 测试流程
        self.is_running = False         # 标志：测试是否正在运行
        self.is_paused = False          # 标志：测试是否处于暂停状态
        self.stop_requested = False     # 标志：用户是否请求停止测试
        self.pause_requested = False    # 标志：用户是否请求暂停测试
        self.skip_item_requested = False # 标志：用户是否请求跳过当前测试项
        self.current_test_thread = None # 当前运行测试逻辑的后台线程
        
        self.create_widgets()

    # ==========================================
    # 界面构建分区
    # ==========================================
    def create_widgets(self):
        """创建并布局测试控制界面的所有组件"""
        
        # --- 状态监控显示区 ---
        status_frame = ttk.LabelFrame(self, text="Status Monitor", padding=30)
        status_frame.pack(fill=tk.X, pady=10)

        # 使用一个容器来居中显示内容
        monitor_container = ttk.Frame(status_frame)
        monitor_container.pack(expand=True)

        # 当前运行状态标签
        self.lbl_status = ttk.Label(monitor_container, text="Current State: STANDBY", font=("Cambria", 16, "bold"), foreground="#605e5c")
        self.lbl_status.pack(pady=10)

        # 进度指示器容器
        progress_info = ttk.Frame(monitor_container)
        progress_info.pack(pady=10)

        self.lbl_remaining = ttk.Label(progress_info, text="Remaining: --", font=("Cambria", 14))
        self.lbl_remaining.pack()

        # --- 控制按钮区 ---
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=30)

        self.btn_start = ttk.Button(btn_frame, text="Start Test", style="Success.TButton", command=self.start_test)
        self.btn_pause = ttk.Button(btn_frame, text="Pause", command=self.pause_test, state=tk.DISABLED)
        self.btn_skip = ttk.Button(btn_frame, text="Skip Item", command=self.skip_to_next, state=tk.DISABLED)
        self.btn_stop = ttk.Button(btn_frame, text="Stop", style="Danger.TButton", command=self.stop_test, state=tk.DISABLED)

        # 统一设置按钮宽度
        self.btn_start.pack(side=tk.LEFT, padx=15, ipadx=10)
        self.btn_pause.pack(side=tk.LEFT, padx=15, ipadx=10)
        self.btn_skip.pack(side=tk.LEFT, padx=15, ipadx=10)
        self.btn_stop.pack(side=tk.LEFT, padx=15, ipadx=10)

    # ==========================================
    # 测试控制逻辑分区
    # ==========================================
    def start_test(self):
        """
        启动测试按钮的回调函数。
        根据当前状态，可能是开启新测试或恢复已暂停的测试。
        """
        if self.btn_start['text'] == "Resume":
            # 如果当前是暂停状态，则执行恢复逻辑
            self.resume_test()
        else:
            # 执行新测试启动逻辑
            if not self.settings_source:
                self.log("Error: Settings source not available", "ERR")
                return

            # 从设置源获取当前配置快照
            settings = self.settings_source.get_current_state()
            self.test_flow = settings.get('test_flow', [])
            
            if not self.test_flow:
                self.log("Error: Test flow is empty. Please add test items in Settings.", "ERR")
                return

            self.current_item_index = 0
            
            # 重置所有控制标志位
            self.is_running = True
            self.is_paused = False
            self.stop_requested = False
            self.pause_requested = False
            
            # 开启后台线程执行核心测试循环
            self.current_test_thread = threading.Thread(target=self.run_test_cycle, daemon=True)
            self.current_test_thread.start()
            
        # 更新 UI 状态为“测试中”
        self.update_ui_state("TESTING")
        self.log("Test Started", "TEST")

    def update_ui_state(self, state):
        """
        根据测试阶段更新 UI 组件的状态。
        """
        if state == "TESTING":
            self.lbl_status.config(text="● TESTING", foreground="#107c10")
            self.btn_start.config(state=tk.DISABLED)
            self.btn_pause.config(state=tk.NORMAL, text="Pause")
            self.btn_skip.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.NORMAL)
        elif state == "PAUSED":
            self.lbl_status.config(text="II PAUSED", foreground="#d13438")
            self.btn_start.config(state=tk.NORMAL, text="Resume")
            self.btn_pause.config(state=tk.DISABLED)
            self.btn_skip.config(state=tk.NORMAL)
        elif state == "STANDBY":
            self.lbl_status.config(text="STANDBY", foreground="#605e5c")
            self.btn_start.config(state=tk.NORMAL, text="Start Test")
            self.btn_pause.config(state=tk.DISABLED, text="Pause")
            self.btn_skip.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.DISABLED)
            self.lbl_remaining.config(text="Remaining: --")

    def run_test_cycle(self):
        """
        核心测试循环逻辑。遍历测试流程中的每一个测试项。
        """
        settings = self.settings_source.get_current_state()
        relay_conn = self.settings_source.get_serial_connection("Relay (Solenoid)")
        motor_x_conn = self.settings_source.get_serial_connection("X-Axis Motor")
        motor_y_conn = self.settings_source.get_serial_connection("Y-Axis Motor")
        
        # --- 串口连接检查 ---
        missing_ports = []
        if not relay_conn or not relay_conn.is_open: missing_ports.append("Relay")
        if not motor_x_conn or not motor_x_conn.is_open: missing_ports.append("X-Axis Motor")
        if not motor_y_conn or not motor_y_conn.is_open: missing_ports.append("Y-Axis Motor")
        
        if missing_ports:
            self.log(f"Error: The following serial ports are not open: {', '.join(missing_ports)}", "ERR")
            self.log("Please open all required serial ports in 'Parameter Settings' tab before starting the test.", "ERR")
            self.is_running = False
            self.lbl_remaining.after(0, self.finish_test)
            return

        press_duration = settings.get('press_duration', 100) / 1000.0
        interval = settings.get('press_interval', 500) / 1000.0

        # 继电器控制指令
        CMD_OPEN = bytes.fromhex("A0 01 01 A2")
        CMD_CLOSE = bytes.fromhex("A0 01 00 A1")

        all_bindings = self.key_manager.get_bindings()
        binding_dict = {b['key_name']: b for b in all_bindings}

        for i in range(len(self.test_flow)):
            if self.stop_requested:
                break
            
            self.current_item_index = i
            item = self.test_flow[i]
            key_name = item['key_name']
            
            # 通知设置页刷新显示（更新正在测试/已完成状态）
            if hasattr(self.settings_source, 'render_test_flow'):
                self.lbl_remaining.after(0, self.settings_source.render_test_flow)
            
            self.log(f"Testing item {i+1}/{len(self.test_flow)}: {key_name}", "TEST")
            
            # 1. 移动电机到指定位置
            binding = binding_dict.get(key_name)
            if binding:
                x_pulse = binding.get('x_pulse', 0)
                y_pulse = binding.get('y_pulse', 0)
                
                self.log(f"Moving to {key_name} (X:{x_pulse}, Y:{y_pulse})", "MOT")
                self.send_motor_pulse(motor_x_conn, x_pulse, "X")
                self.send_motor_pulse(motor_y_conn, y_pulse, "Y")
                
                # 等待电机移动（这里暂时用固定延时，实际可能需要查询状态）
                # 在等待期间也要检查停止请求
                for _ in range(20): # 2秒，每100ms检查一次
                    if self.stop_requested or self.skip_item_requested: break
                    time.sleep(0.1)
            else:
                self.log(f"Warning: No binding found for {key_name}", "WRN")

            if self.stop_requested: break
            if self.skip_item_requested:
                self.skip_item_requested = False
                continue

            # 2. 初始化该项的剩余值
            mode = item.get('mode')
            target = item.get('target', 0)
            
            if mode == 'time':
                unit = item.get('unit', 'Seconds')
                seconds = target
                if unit == 'Minutes': seconds = target * 60
                elif unit == 'Hours': seconds = target * 3600
                self.remaining_seconds = seconds
                self.lbl_remaining.after(0, lambda: self.update_remaining_display(mode))
                
                # 启动时间模式下的 UI 倒计时
                self.lbl_remaining.after(0, self.run_timer_async)
            else:
                self.remaining_counts = target
                self.lbl_remaining.after(0, lambda: self.update_remaining_display(mode))

            # 3. 执行单项测试循环
            while self.is_running:
                if self.stop_requested or self.skip_item_requested: break
                
                # 检查暂停
                if self.pause_requested:
                    self.is_paused = True
                    while self.pause_requested and not self.stop_requested:
                        time.sleep(0.1)
                    self.is_paused = False
                    if self.stop_requested: break

                # 执行动作
                try:
                    # 吸合继电器
                    relay_conn.write(CMD_OPEN)
                    self.log(f"Relay ON: {CMD_OPEN.hex(' ').upper()}", "COM")
                    time.sleep(press_duration)
                    
                    # 断开继电器
                    relay_conn.write(CMD_CLOSE)
                    self.log(f"Relay OFF: {CMD_CLOSE.hex(' ').upper()}", "COM")
                    time.sleep(interval)
                except Exception as e:
                    self.log(f"Relay Error: {e}", "ERR")
                    break

                if mode == 'count':
                    self.remaining_counts -= 1
                    self.lbl_remaining.after(0, lambda: self.update_remaining_display(mode))
                    if self.remaining_counts <= 0:
                        break
                else:
                    if self.remaining_seconds <= 0:
                        break
            
            self.skip_item_requested = False
            if self.stop_requested: break

        # 收尾
        self.is_running = False
        self.current_item_index = len(self.test_flow) # 全部标记为已完成
        if hasattr(self.settings_source, 'render_test_flow'):
            self.lbl_remaining.after(0, self.settings_source.render_test_flow)
        self.lbl_remaining.after(0, self.finish_test)

    def update_remaining_display(self, mode):
        """更新剩余时间/次数显示"""
        if mode == 'time':
            m, s = divmod(self.remaining_seconds, 60)
            h, m = divmod(m, 60)
            self.lbl_remaining.config(text=f"Item {self.current_item_index+1}: {h:02d}:{m:02d}:{s:02d}")
        else:
            self.lbl_remaining.config(text=f"Item {self.current_item_index+1}: {self.remaining_counts} Counts")

    def run_timer_async(self):
        """异步更新时间"""
        if not self.is_running or self.is_paused:
            if self.is_running: # 如果还在运行只是暂停，1秒后再试
                self.timer_id = self.after(1000, self.run_timer_async)
            return

        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.update_remaining_display('time')
            self.timer_id = self.after(1000, self.run_timer_async)
        else:
            self.timer_id = None

    def send_motor_pulse(self, conn, pulse, axis_name=""):
        """发送电机脉冲指令 (Modbus RTU)"""
        if not conn or not conn.is_open:
            return
        try:
            # 1. 设置脉冲数 (寄存器 0x05)
            data = struct.pack('>BBHH', 0x01, 0x06, 0x05, pulse)
            crc = self.calculate_crc(data)
            full_msg = data + struct.pack('<H', crc)
            conn.write(full_msg)
            self.log(f"Motor {axis_name} Set Pulse ({pulse}): {full_msg.hex(' ').upper()}", "COM")
            
            # 2. 发送运行指令 (寄存器 0x02, 值 1)
            time.sleep(0.1)
            data = struct.pack('>BBHH', 0x01, 0x06, 0x02, 0x0001)
            crc = self.calculate_crc(data)
            full_msg = data + struct.pack('<H', crc)
            conn.write(full_msg)
            self.log(f"Motor {axis_name} Run: {full_msg.hex(' ').upper()}", "COM")
        except Exception as e:
            self.log(f"Motor {axis_name} Command Error: {e}", "ERR")

    def calculate_crc(self, data):
        """计算 Modbus CRC16"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    # ==========================================
    # 辅助与生命周期管理分区
    # ==========================================
    def finish_test(self):
        """测试完成或被手动停止后的清理工作，重置界面状态。"""
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
        self.update_ui_state("STANDBY")
        self.log("Test Finished/Stopped", "TEST")

    def pause_test(self):
        """暂停测试按钮的回调。设置请求标志并停止 UI 定时器。"""
        self.pause_requested = True
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
        self.update_ui_state("PAUSED")
        self.log("Test Pause Requested (waiting for cycle to finish)", "TEST")

    def resume_test(self):
        """恢复测试按钮的回调。清除请求标志并重启 UI 定时器（如果需要）。"""
        self.pause_requested = False # 解除后台线程的阻塞
        settings = self.settings_source.get_current_state()
        if settings.get('test_mode') == 'time':
            self.run_timer()
        self.update_ui_state("TESTING")
        self.log("Test Resumed", "TEST")

    def stop_test(self):
        """停止测试按钮的回调。设置停止请求标志，并确保暂停状态被解除。"""
        self.stop_requested = True
        self.pause_requested = False # 如果处于暂停状态，先解封线程使其能检测到停止标志并退出
        self.log("Test Stop Requested (waiting for cycle to finish)", "TEST")

    def skip_to_next(self):
        """跳过当前测试项"""
        if self.is_running:
            self.skip_item_requested = True
            self.log("Skipping to next test item...", "TEST")
