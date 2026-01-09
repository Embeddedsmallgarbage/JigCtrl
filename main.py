import tkinter as tk
from tkinter import ttk
from ui_motion import MotionControlFrame
from ui_settings import SettingsFrame
from ui_test_control import TestControlFrame
from ui_log import LogFrame

class JigCtrlApp(tk.Tk):
    """
    JigCtrlApp 类：应用程序的主窗口类，继承自 tk.Tk。
    负责初始化主界面、配置全局样式以及管理各个功能页签。
    """
    def __init__(self):
        super().__init__()
        # 设置窗口标题
        self.title("JigCtrl - Remote Control Jig System")
        # 设置窗口初始大小
        self.geometry("800x600")
        
        # --- 1. 样式配置 ---
        self.configure_styles()

        # --- 2. 界面组件创建 ---
        self.create_widgets()
        
        # --- 3. 绑定窗口关闭事件 ---
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def configure_styles(self):
        """
        配置应用程序的全局 ttk 样式。
        设置统一的字体、背景颜色以及各个组件的具体样式。
        """
        style = ttk.Style(self)
        try:
            # 尝试使用 'clam' 主题以获得更好的跨平台一致性
            style.theme_use('clam') 
        except:
            pass
        
        # 全局字体和背景颜色设置
        default_font = ("Cambria", 10)
        style.configure(".", font=default_font, background="white")
        
        # --- 特定组件样式配置 ---
        # 框架背景颜色
        style.configure("TFrame", background="white")
        # 标签框架样式
        style.configure("TLabelframe", background="white")
        style.configure("TLabelframe.Label", background="white", font=("Cambria", 10, "bold"))
        # 标签样式
        style.configure("TLabel", background="white", font=("Cambria", 10))
        # 按钮样式
        style.configure("TButton", font=("Cambria", 10), background="white")
        # 方向控制按钮样式 (加粗字体)
        style.configure("Dir.TButton", font=("Cambria", 12, "bold"), background="white")
        
        # 输入框和下拉框的背景色配置
        style.configure("TEntry", fieldbackground="white")
        style.configure("TCombobox", fieldbackground="white", background="white")
        
        # 选项卡 (Notebook) 样式配置
        style.configure("TNotebook", background="white")
        style.configure("TNotebook.Tab", font=("Cambria", 10))

        # 确保根窗口背景也是白色
        self.configure(background="white")

    def create_widgets(self):
        """
        创建并组织主界面上的所有功能组件。
        使用 Notebook (页签) 控件来组织不同的功能模块。
        """
        # 创建主页签控件
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- 初始化功能页签 ---
        
        # 1. 日志页签 (最先初始化，以便其他页签可以调用其日志记录功能)
        self.tab_log = LogFrame(self.notebook)
        
        # 2. 运动控制页签
        self.tab_motion = MotionControlFrame(self.notebook, log_callback=self.tab_log.add_log)
        
        # 3. 参数设置页签
        self.tab_settings = SettingsFrame(self.notebook, log_callback=self.tab_log.add_log)
        
        # 4. 测试控制页签 (传入设置页签引用，以便读取配置信息)
        self.tab_test = TestControlFrame(self.notebook, settings_source=self.tab_settings, log_callback=self.tab_log.add_log)

        # 将页签添加到 Notebook 中显示
        self.notebook.add(self.tab_motion, text="Motion Control")
        self.notebook.add(self.tab_settings, text="Parameter Settings")
        self.notebook.add(self.tab_test, text="Test Control")
        self.notebook.add(self.tab_log, text="Logs")

    def on_closing(self):
        """
        窗口关闭时的回调函数。
        在关闭前自动保存配置。
        """
        # 保存设置页签的配置
        self.tab_settings.save_config_to_file()
        # 关闭窗口
        self.destroy()

# --- 程序入口 ---
if __name__ == "__main__":
    app = JigCtrlApp()
    app.mainloop()
