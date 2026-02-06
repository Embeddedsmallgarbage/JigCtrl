import tkinter as tk
from tkinter import ttk, messagebox
from key_manager import KeyManager

class KeySelectionWindow:
    """
    KeySelectionWindow 类：按键选择窗口。
    提供按键列表显示、双击选择、添加自定义按键等功能。
    """
    
    def __init__(self, parent, key_manager: KeyManager, on_select_callback):
        """
        初始化按键选择窗口。
        
        :param parent: 父窗口
        :param key_manager: 按键管理器实例
        :param on_select_callback: 选择按键后的回调函数，接收按键名称作为参数
        """
        self.parent = parent
        self.key_manager = key_manager
        self.on_select_callback = on_select_callback
        self.selected_key = None
        
        self.create_window()
        self.load_keys()
    
    def create_window(self):
        """创建窗口和UI组件"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Select Key")
        self.window.geometry("600x500")
        self.window.resizable(False, False)
        self.window.configure(bg="white")
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # 主容器
        main_container = ttk.Frame(self.window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧：分类列表
        left_frame = ttk.LabelFrame(main_container, text="Key Categories", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        
        self.category_listbox = tk.Listbox(left_frame, width=20, font=("Cambria", 10))
        self.category_listbox.pack(fill=tk.BOTH, expand=True)
        self.category_listbox.bind('<<ListboxSelect>>', self.on_category_select)
        
        # 右侧：按键列表
        right_frame = ttk.LabelFrame(main_container, text="Key List (Double-click to select)", padding=10)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.key_listbox = tk.Listbox(right_frame, width=30, font=("Cambria", 10))
        self.key_listbox.pack(fill=tk.BOTH, expand=True)
        self.key_listbox.bind('<Double-Button-1>', self.on_key_double_click)
        
        # 底部：添加自定义按键区域
        bottom_frame = ttk.LabelFrame(self.window, text="Add Custom Key", padding=10)
        bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # 分类选择
        ttk.Label(bottom_frame, text="Category:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.custom_category_var = tk.StringVar()
        self.custom_category_combo = ttk.Combobox(
            bottom_frame,
            textvariable=self.custom_category_var,
            state="readonly",
            width=15
        )
        self.custom_category_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 按键名称输入
        ttk.Label(bottom_frame, text="Key Name:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.custom_key_var = tk.StringVar()
        ttk.Entry(bottom_frame, textvariable=self.custom_key_var, width=20).grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        # 添加按钮
        ttk.Button(bottom_frame, text="Add", command=self.add_custom_key, width=10).grid(row=0, column=4, padx=5, pady=5)
        
        # 底部按钮区域
        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(btn_frame, text="Cancel", command=self.window.destroy, width=10).pack(side=tk.RIGHT, padx=5)
    
    def load_keys(self):
        """加载所有按键到分类列表"""
        all_keys = self.key_manager.get_all_keys()
        
        self.category_listbox.delete(0, tk.END)
        for category in all_keys.keys():
            self.category_listbox.insert(tk.END, category)
        
        # 默认选择第一个分类
        if self.category_listbox.size() > 0:
            self.category_listbox.selection_set(0)
            first_category = list(all_keys.keys())[0]
            self.load_keys_for_category(first_category)
        
        # 更新自定义按键的分类下拉框
        self.update_custom_category_combo(all_keys)
    
    def update_custom_category_combo(self, all_keys):
        """更新自定义按键的分类下拉框"""
        categories = list(all_keys.keys())
        if "Other" not in categories:
            categories.append("Other")
        
        self.custom_category_combo['values'] = categories
        if categories:
            self.custom_category_combo.set(categories[0])
    
    def on_category_select(self, event):
        """分类选择事件处理"""
        selection = self.category_listbox.curselection()
        if selection:
            category = self.category_listbox.get(selection[0])
            all_keys = self.key_manager.get_all_keys()
            self.load_keys_for_category(category)
    
    def load_keys_for_category(self, category):
        """加载指定分类的按键"""
        self.key_listbox.delete(0, tk.END)
        all_keys = self.key_manager.get_all_keys()
        
        if category in all_keys:
            for key in all_keys[category]:
                self.key_listbox.insert(tk.END, key)
    
    def on_key_double_click(self, event):
        """按键双击事件处理"""
        selection = self.key_listbox.curselection()
        if selection:
            key_name = self.key_listbox.get(selection[0])
            self.selected_key = key_name
            self.window.destroy()
            
            if self.on_select_callback:
                self.on_select_callback(key_name)
    
    def add_custom_key(self):
        """添加自定义按键"""
        category = self.custom_category_var.get().strip()
        key_name = self.custom_key_var.get().strip()
        
        if not category:
            messagebox.showerror("错误", "请选择分类")
            return
        
        if not key_name:
            messagebox.showerror("错误", "请输入按键名称")
            return
        
        # 添加自定义按键
        success = self.key_manager.add_custom_key(category, key_name)
        
        if success:
            messagebox.showinfo("成功", f"已添加自定义按键: {key_name}")
            self.custom_key_var.set("")
            
            # 重新加载按键列表
            self.load_keys()
            
            # 切换到新添加的分类
            for i in range(self.category_listbox.size()):
                if self.category_listbox.get(i) == category:
                    self.category_listbox.selection_set(i)
                    self.load_keys_for_category(category)
                    break
        else:
            messagebox.showwarning("警告", f"按键 '{key_name}' 已存在于分类 '{category}' 中")
    
    def get_selected_key(self):
        """获取选择的按键"""
        return self.selected_key
