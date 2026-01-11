import tkinter as tk
from tkinter import ttk
import datetime
import time
import threading

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
        self.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # --- 测试状态变量 ---
        self.timer_id = None            # Tkinter 定时器 ID，用于倒计时更新
        self.remaining_seconds = 0      # 剩余测试时间（秒）
        self.remaining_counts = 0       # 剩余测试次数
        self.is_running = False         # 标志：测试是否正在运行
        self.is_paused = False          # 标志：测试是否处于暂停状态
        self.stop_requested = False     # 标志：用户是否请求停止测试
        self.pause_requested = False    # 标志：用户是否请求暂停测试
        self.current_test_thread = None # 当前运行测试逻辑的后台线程
        
        self.create_widgets()

    # ==========================================
    # 界面构建分区
    # ==========================================
    def create_widgets(self):
        """创建并布局测试控制界面的所有组件"""
        
        # --- 状态监控显示区 ---
        status_frame = ttk.LabelFrame(self, text="Status Monitor", padding=20)
        status_frame.pack(fill=tk.X, pady=10)

        # 当前运行状态标签 (STANDBY / TESTING / PAUSED)
        self.lbl_status = ttk.Label(status_frame, text="Current State: STANDBY", font=("Cambria", 14, "bold"), foreground="gray")
        self.lbl_status.pack(pady=5)

        # 剩余时间或次数显示标签
        self.lbl_remaining = ttk.Label(status_frame, text="Remaining: --", font=("Cambria", 12))
        self.lbl_remaining.pack(pady=5)

        # --- 控制按钮区 ---
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)

        self.btn_start = ttk.Button(btn_frame, text="Start Test", command=self.start_test)
        self.btn_pause = ttk.Button(btn_frame, text="Pause", command=self.pause_test, state=tk.DISABLED)
        self.btn_stop = ttk.Button(btn_frame, text="Stop", command=self.stop_test, state=tk.DISABLED)

        self.btn_start.pack(side=tk.LEFT, padx=10)
        self.btn_pause.pack(side=tk.LEFT, padx=10)
        self.btn_stop.pack(side=tk.LEFT, padx=10)

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
            mode = settings.get('test_mode')
            target = settings.get('target_value', 0)
            
            # 根据测试模式（时间或次数）初始化剩余值
            if mode == 'time':
                unit = settings.get('time_unit', 'Seconds')
                if unit == 'Minutes':
                    self.remaining_seconds = target * 60
                elif unit == 'Hours':
                    self.remaining_seconds = target * 3600
                else:
                    self.remaining_seconds = target
                
                # 初始化时间显示格式 H:M:S
                m, s = divmod(self.remaining_seconds, 60)
                h, m = divmod(m, 60)
                self.lbl_remaining.config(text=f"Remaining: {h:02d}:{m:02d}:{s:02d}")
            else:
                self.remaining_counts = target
                self.lbl_remaining.config(text=f"Remaining: {self.remaining_counts} (Counts)")
            
            # 重置所有控制标志位
            self.is_running = True
            self.is_paused = False
            self.stop_requested = False
            self.pause_requested = False
            
            # 开启后台线程执行核心测试循环，避免阻塞 UI 界面
            self.current_test_thread = threading.Thread(target=self.run_test_cycle, daemon=True)
            self.current_test_thread.start()
            
            # 如果是时间模式，启动界面倒计时更新
            if mode == 'time':
                self.run_timer()
            
        # 更新 UI 状态为“测试中”
        self.update_ui_state("TESTING")
        self.log("Test Started", "TEST")

    def update_ui_state(self, state):
        """
        根据测试阶段更新 UI 组件的状态（启用/禁用按钮、颜色等）。
        
        :param state: 目标状态字符串 ("TESTING", "PAUSED", "STANDBY")
        """
        if state == "TESTING":
            self.lbl_status.config(text="Current State: TESTING", foreground="green")
            self.btn_start.config(state=tk.DISABLED)
            self.btn_pause.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.NORMAL)
        elif state == "PAUSED":
            self.lbl_status.config(text="Current State: PAUSED", foreground="orange")
            self.btn_start.config(state=tk.NORMAL, text="Resume")
            self.btn_pause.config(state=tk.DISABLED)
        elif state == "STANDBY":
            self.lbl_status.config(text="Current State: STANDBY", foreground="gray")
            self.btn_start.config(state=tk.NORMAL, text="Start Test")
            self.btn_pause.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.DISABLED)
            self.lbl_remaining.config(text="Remaining: --")

    def run_timer(self):
        """
        UI 定时器回调函数。每隔一秒调用一次，用于更新界面上的剩余时间显示。
        """
        if not self.is_running or self.is_paused:
            return

        if self.remaining_seconds >= 0:
            m, s = divmod(self.remaining_seconds, 60)
            h, m = divmod(m, 60)
            self.lbl_remaining.config(text=f"Remaining: {h:02d}:{m:02d}:{s:02d}")
            
            if self.remaining_seconds == 0:
                # 时间到，通知后台循环线程停止
                self.stop_requested = True 
                return

            self.remaining_seconds -= 1
            # 安排下一秒的更新
            self.timer_id = self.after(1000, self.run_timer)

    # ==========================================
    # 核心测试循环逻辑分区 (运行在独立线程)
    # ==========================================
    def run_test_cycle(self):
        """
        核心测试循环逻辑。该方法运行在独立的后台线程中，通过操作串口来控制硬件。
        包含暂停、停止响应逻辑以及继电器控制指令。
        """
        # 获取最新的设置和串口连接
        settings = self.settings_source.get_current_state()
        relay_conn = self.settings_source.get_serial_connection("Relay (Solenoid)")
        
        # 转换参数单位（毫秒 -> 秒）
        press_duration = settings.get('press_duration', 100) / 1000.0
        interval = settings.get('press_interval', 500) / 1000.0
        mode = settings.get('test_mode')

        # 继电器控制十六进制指令（示例）
        CMD_OPEN = bytes.fromhex("A0 01 01 A2")
        CMD_CLOSE = bytes.fromhex("A0 01 00 A1")

        while self.is_running:
            # 检查是否请求停止
            if self.stop_requested:
                break
            
            # 检查是否请求暂停
            if self.pause_requested:
                self.is_paused = True
                while self.pause_requested: # 阻塞线程直至恢复或停止
                    time.sleep(0.1)
                    if self.stop_requested:
                        break
                self.is_paused = False
                if self.stop_requested:
                    break

            # --- 执行单次测试循环 (Cycle Start) ---
            # 1. 打开继电器
            try:
                if relay_conn and relay_conn.is_open:
                    relay_conn.write(CMD_OPEN)
                    self.log("Relay OPEN", "REL")
            except Exception as e:
                self.log(f"Error writing to Relay: {e}", "ERR")

            # 保持打开状态的时间
            time.sleep(press_duration)

            # 2. 关闭继电器
            try:
                if relay_conn and relay_conn.is_open:
                    relay_conn.write(CMD_CLOSE)
                    self.log("Relay CLOSE", "REL")
            except Exception as e:
                self.log(f"Error writing to Relay: {e}", "ERR")
            
            # 两次动作之间的间隔时间
            time.sleep(interval)
            # --- 单次测试循环结束 (Cycle End) ---

            # 如果是次数模式，更新剩余次数并通知 UI
            if mode == 'count':
                self.remaining_counts -= 1
                # 使用 after 方法安全地从子线程请求 UI 更新
                self.lbl_remaining.after(0, lambda: self.lbl_remaining.config(text=f"Remaining: {self.remaining_counts} (Counts)"))
                
                if self.remaining_counts <= 0:
                    break
        
        # 循环结束后的收尾工作
        self.is_running = False
        self.lbl_remaining.after(0, self.finish_test)

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
