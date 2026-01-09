import tkinter as tk
from tkinter import ttk

class MotionControlFrame(ttk.Frame):
    """
    MotionControlFrame 类：运动控制界面类，继承自 ttk.Frame。
    提供方向键控制按钮以及键盘快捷键绑定功能，用于控制电机的运动。
    """
    def __init__(self, master=None, log_callback=None):
        super().__init__(master)
        # --- 成员变量初始化 ---
        # 日志回调函数，若未提供则默认使用 print
        self.log = log_callback if log_callback else print
        
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
    def on_btn_click(self, direction):
        """
        处理方向按钮点击事件。
        参数:
            direction: 方向字符串 ('Up', 'Down', 'Left', 'Right')
        """
        self.log(f"Button clicked: {direction}", "MOT")
        # --- 在此处添加发送串口指令控制电机的逻辑 ---

    def animate_press(self, direction, is_pressed):
        """
        键盘快捷键按下/释放时的视觉动画效果。
        参数:
            direction: 方向字符串
            is_pressed: 布尔值，True 表示按下，False 表示释放
        """
        btn = self.buttons.get(direction)
        if not btn:
            return
        
        if is_pressed:
            # 将按钮状态设为按下 (UI 视觉反馈)
            btn.state(['pressed'])
            self.log(f"Key pressed: {direction}", "MOT")
            # --- 此处可添加按下键盘时的电机启动逻辑 ---
        else:
            # 移除按钮按下状态
            btn.state(['!pressed'])
            self.log(f"Key released: {direction}", "MOT")
            # --- 此处可添加松开键盘时的电机停止逻辑 ---
