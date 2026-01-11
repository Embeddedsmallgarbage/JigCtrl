import tkinter as tk
from tkinter import ttk
import threading
import time
from modbus_comm import ModBusComm

class MotionControlFrame(ttk.Frame):
    """
    MotionControlFrame 类：运动控制界面类，继承自 ttk.Frame。
    提供方向键控制按钮以及键盘快捷键绑定功能，用于控制电机的运动。
    """
    def __init__(self, master=None, log_callback=None, settings_frame=None):
        super().__init__(master)
        # --- 成员变量初始化 ---
        # 日志回调函数，若未提供则默认使用 print
        self.log = log_callback if log_callback else print
        
        # 设置页面引用，用于获取参数配置
        self.settings_frame = settings_frame
        
        # X 轴电机控制相关变量
        self.x_axis_revolutions = 0
        self.x_axis_max_revolutions = 100
        self.x_axis_initialized = False
        self.x_axis_direction = None
        self.x_axis_speed = 100
        self.x_axis_running = False
        self.x_axis_stop_requested = False
        
        # 按键状态跟踪
        self.key_pressed = {
            'Left': False,
            'Right': False
        }
        
        # ModBus 通信对象
        self.modbus = ModBusComm(device_address=1, log_callback=self.log)
        
        # 长按控制线程
        self.long_press_thread = None
        self.long_press_running = False
        
        # 填充父容器并设置内边距
        self.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 创建界面组件
        self.create_widgets()
        # 绑定键盘快捷键
        self.bind_keys()

    # =========================================================================
    # 界面构建分区 (UI Construction)
    # =========================================================================
    def create_widgets(self):
        """
        创建运动控制界面的所有子组件，主要是十字型布局的方向控制按钮。
        """
        # 创建一个容器框架用于居中放置按钮
        self.control_container = ttk.Frame(self)
        self.control_container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # 按钮样式配置
        style = ttk.Style()
        style.configure("Dir.TButton", font=("Arial", 12, "bold"), width=8)

        # --- 方向按钮创建 ---
        # 使用 lambda 函数传递方向参数给统一的点击处理函数
        self.btn_up = ttk.Button(self.control_container, text="↑(Up)", style="Dir.TButton", command=lambda: self.on_btn_click('Up'))
        self.btn_left = ttk.Button(self.control_container, text="←(Left)", style="Dir.TButton", command=lambda: self.on_btn_click('Left'))
        self.btn_down = ttk.Button(self.control_container, text="↓(Down)", style="Dir.TButton", command=lambda: self.on_btn_click('Down'))
        self.btn_right = ttk.Button(self.control_container, text="→(Right)", style="Dir.TButton", command=lambda: self.on_btn_click('Right'))

        # --- 按钮网格布局 (十字架形状) ---
        #       [Up]
        # [Left] [Down] [Right]
        self.btn_up.grid(row=0, column=1, padx=5, pady=5)
        self.btn_left.grid(row=1, column=0, padx=5, pady=5)
        self.btn_down.grid(row=1, column=1, padx=5, pady=5)
        self.btn_right.grid(row=1, column=2, padx=5, pady=5)

        # 视觉反馈映射字典，用于通过方向字符串快速找到对应的按钮对象
        self.buttons = {
            'Up': self.btn_up,
            'Down': self.btn_down,
            'Left': self.btn_left,
            'Right': self.btn_right
        }

    # =========================================================================
    # 事件绑定分区 (Event Bindings)
    # =========================================================================
    def bind_keys(self):
        """
        绑定页面可见性相关的事件，确保快捷键仅在该页签可见时生效。
        """
        # 绑定当页签变为可见时的事件
        self.bind('<Visibility>', self.on_visibility)
        # 绑定当页签变为不可见时的事件
        self.bind('<Unmap>', self.on_unmap)

    def on_visibility(self, event):
        """
        当运动控制页签被激活/可见时，启用全局键盘绑定。
        参数:
            event: tkinter 事件对象
        """
        top = self.winfo_toplevel() # 获取主窗口
        
        # --- 绑定方向键按下与释放事件 ---
        # 绑定 Up 键
        self.bind_id_press_up = top.bind('<KeyPress-Up>', lambda e: self.animate_press('Up', True))
        self.bind_id_release_up = top.bind('<KeyRelease-Up>', lambda e: self.animate_press('Up', False))
        # 绑定 Down 键
        self.bind_id_press_down = top.bind('<KeyPress-Down>', lambda e: self.animate_press('Down', True))
        self.bind_id_release_down = top.bind('<KeyRelease-Down>', lambda e: self.animate_press('Down', False))
        # 绑定 Left 键
        self.bind_id_press_left = top.bind('<KeyPress-Left>', lambda e: self.animate_press('Left', True))
        self.bind_id_release_left = top.bind('<KeyRelease-Left>', lambda e: self.animate_press('Left', False))
        # 绑定 Right 键
        self.bind_id_press_right = top.bind('<KeyPress-Right>', lambda e: self.animate_press('Right', True))
        self.bind_id_release_right = top.bind('<KeyRelease-Right>', lambda e: self.animate_press('Right', False))
        
        # 使当前 Frame 获得焦点
        self.focus_set()

    def on_unmap(self, event):
        """
        当切换到其他页签时，解除键盘绑定，防止误触发电机运动。
        参数:
            event: tkinter 事件对象
        """
        top = self.winfo_toplevel()
        try:
            # 依次解除所有已绑定的事件 ID
            top.unbind('<KeyPress-Up>', self.bind_id_press_up)
            top.unbind('<KeyRelease-Up>', self.bind_id_release_up)
            top.unbind('<KeyPress-Down>', self.bind_id_press_down)
            top.unbind('<KeyRelease-Down>', self.bind_id_release_down)
            top.unbind('<KeyPress-Left>', self.bind_id_press_left)
            top.unbind('<KeyRelease-Left>', self.bind_id_release_left)
            top.unbind('<KeyPress-Right>', self.bind_id_press_right)
            top.unbind('<KeyRelease-Right>', self.bind_id_release_right)
        except (tk.TclError, AttributeError):
            # 忽略解绑过程中可能出现的错误（如 ID 不存在）
            pass

    # =========================================================================
    # 逻辑处理分区 (Logic Handling)
    # =========================================================================
    
    def get_x_axis_serial_connection(self):
        """
        获取 X 轴电机的串口连接。
        """
        if self.settings_frame:
            return self.settings_frame.get_serial_connection("X-Axis Motor")
        return None
    
    def get_motor_speed(self):
        """
        从设置页面获取电机速度。
        """
        if self.settings_frame and hasattr(self.settings_frame, 'vars'):
            try:
                return self.settings_frame.vars['motor_speed'].get()
            except:
                pass
        return 100
    
    def initialize_x_axis_motor(self, forward=True):
        """
        初始化 X 轴电机参数。
        
        :param forward: True=正转（右方向），False=反转（左方向）
        :return: 是否成功
        """
        serial_conn = self.get_x_axis_serial_connection()
        if not serial_conn:
            self.log("X-Axis motor serial connection not available", "ERR")
            return False
        
        speed = self.get_motor_speed()
        revolutions = 1
        
        if self.modbus.initialize_motor(serial_conn, speed, revolutions, forward):
            self.x_axis_initialized = True
            self.x_axis_direction = 'forward' if forward else 'reverse'
            self.x_axis_speed = speed
            self.log(f"X-Axis motor initialized: speed={speed} r/min, revolutions={revolutions}, direction={'forward' if forward else 'reverse'}", "MOT")
            return True
        else:
            self.log("Failed to initialize X-Axis motor", "ERR")
            return False
    
    def run_x_axis_motor(self):
        """
        运行 X 轴电机。
        
        :return: 是否成功
        """
        serial_conn = self.get_x_axis_serial_connection()
        if not serial_conn:
            self.log("X-Axis motor serial connection not available", "ERR")
            return False
        
        if self.modbus.run_motor(serial_conn):
            self.x_axis_running = True
            self.log("X-Axis motor started", "MOT")
            return True
        else:
            self.log("Failed to start X-Axis motor", "ERR")
            return False
    
    def stop_x_axis_motor(self):
        """
        停止 X 轴电机。
        
        :return: 是否成功
        """
        serial_conn = self.get_x_axis_serial_connection()
        if not serial_conn:
            return False
        
        if self.modbus.stop_motor(serial_conn):
            self.x_axis_running = False
            self.x_axis_stop_requested = True
            self.log("X-Axis motor stopped", "MOT")
            return True
        return False
    
    def update_revolutions(self, forward):
        """
        更新圈数并检查边界。
        
        :param forward: True=正转（加圈数），False=反转（减圈数）
        :return: 是否可以继续运行
        """
        if forward:
            if self.x_axis_revolutions < self.x_axis_max_revolutions:
                self.x_axis_revolutions += 1
                self.log(f"X-Axis revolutions: {self.x_axis_revolutions}/{self.x_axis_max_revolutions}", "MOT")
                return True
            else:
                self.log(f"X-Axis reached maximum revolutions ({self.x_axis_max_revolutions})", "MOT")
                return False
        else:
            if self.x_axis_revolutions > 0:
                self.x_axis_revolutions -= 1
                self.log(f"X-Axis revolutions: {self.x_axis_revolutions}/{self.x_axis_max_revolutions}", "MOT")
                return True
            else:
                self.log(f"X-Axis reached minimum revolutions (0)", "MOT")
                return False
    
    def on_btn_click(self, direction):
        """
        处理方向按钮点击事件（X轴：左/右方向）。
        参数:
            direction: 方向字符串 ('Up', 'Down', 'Left', 'Right')
        """
        self.log(f"Button clicked: {direction}", "MOT")
        
        # 只处理 X 轴方向（左/右）
        if direction not in ['Left', 'Right']:
            return
        
        # 检查串口连接是否可用（大前提）
        serial_conn = self.get_x_axis_serial_connection()
        if not serial_conn:
            self.log("X-Axis motor serial connection not available", "ERR")
            return
        
        forward = (direction == 'Right')
        
        # 检查边界
        if not self.update_revolutions(forward):
            return
        
        # 初始化电机（如果未初始化或方向改变）
        if not self.x_axis_initialized or (self.x_axis_direction != ('forward' if forward else 'reverse')):
            if not self.initialize_x_axis_motor(forward):
                return
        
        # 运行电机
        self.run_x_axis_motor()
        
        # 等待电机运行完成（一圈）
        threading.Thread(target=self.wait_for_motor_completion, daemon=True).start()
    
    def wait_for_motor_completion(self):
        """
        等待电机运行完成（一圈）。
        """
        # 简单的等待逻辑，实际应该根据电机速度计算等待时间
        # 假设电机速度为 r/min，一圈需要 60/speed 秒
        speed = self.x_axis_speed
        if speed > 0:
            wait_time = 60.0 / speed
            time.sleep(wait_time)
        
        # 电机运行完成后，自动停止
        if self.x_axis_running and not self.x_axis_stop_requested:
            self.stop_x_axis_motor()
    
    def animate_press(self, direction, is_pressed):
        """
        键盘快捷键按下/释放时的处理（支持长按）。
        参数:
            direction: 方向字符串
            is_pressed: 布尔值，True 表示按下，False 表示释放
        """
        # 只处理 X 轴方向（左/右）
        if direction not in ['Left', 'Right']:
            btn = self.buttons.get(direction)
            if btn:
                if is_pressed:
                    btn.state(['pressed'])
                else:
                    btn.state(['!pressed'])
            return
        
        btn = self.buttons.get(direction)
        if not btn:
            return
        
        forward = (direction == 'Right')
        
        if is_pressed:
            btn.state(['pressed'])
            self.key_pressed[direction] = True
            self.log(f"Key pressed: {direction}", "MOT")
            
            # 检查串口连接是否可用（大前提）
            serial_conn = self.get_x_axis_serial_connection()
            if not serial_conn:
                self.log("X-Axis motor serial connection not available", "ERR")
                return
            
            # 检查边界
            if not self.update_revolutions(forward):
                return
            
            # 初始化电机（如果未初始化或方向改变）
            if not self.x_axis_initialized or (self.x_axis_direction != ('forward' if forward else 'reverse')):
                if not self.initialize_x_axis_motor(forward):
                    return
            
            # 运行电机
            self.run_x_axis_motor()
            
            # 启动长按控制线程
            if not self.long_press_running:
                self.long_press_running = True
                self.x_axis_stop_requested = False
                self.long_press_thread = threading.Thread(target=self.long_press_control, args=(direction,), daemon=True)
                self.long_press_thread.start()
        else:
            btn.state(['!pressed'])
            self.key_pressed[direction] = False
            self.log(f"Key released: {direction}", "MOT")
            
            # 停止电机
            self.stop_x_axis_motor()
    
    def long_press_control(self, direction):
        """
        长按控制线程，持续运行电机直到按键释放。
        """
        forward = (direction == 'Right')
        
        while self.long_press_running and self.key_pressed[direction]:
            # 检查是否需要停止
            if self.x_axis_stop_requested:
                break
            
            # 等待电机运行完成（一圈）
            speed = self.x_axis_speed
            if speed > 0:
                wait_time = 60.0 / speed
                time.sleep(wait_time)
            
            # 如果按键仍然按下，继续运行
            if self.key_pressed[direction]:
                # 检查边界
                if not self.update_revolutions(forward):
                    break
                
                # 运行电机
                self.run_x_axis_motor()
            else:
                break
        
        self.long_press_running = False
        self.x_axis_stop_requested = False
