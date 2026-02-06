import json
import os
from typing import Dict, List, Any, Optional

class KeyManager:
    """
    KeyManager 类：按键配置管理器，负责按键配置的持久化存储和加载。
    使用 JSON 格式保存配置文件到本地。
    配置文件保存在程序所在目录下的 config 文件夹中。
    """
    
    # 内置按键分类和按键列表（从Keys.md中提取）
    BUILTIN_KEYS = {
        "Basic Keys": [
            "Input", "Power", "Back", "Home", "Guide", "Mute", "Volume+", "Volume-",
            "Program+", "Program-", "Bookmark", "Dashboard", "Assistant", "Subtitle",
            "Multilingual", "Live TV", "Program List", "Recall", "Info", "AI-app",
            "Learning Setting", "TV input"
        ],
        "Navigation Keys": [
            "D-pad up", "D-pad down", "D-pad left", "D-pad right", "D-pad center"
        ],
        "Color Keys": [
            "Red", "Green", "Yellow", "Blue"
        ],
        "Streaming Platform Keys": [
            "PRIME VIDEO", "YOUTUBE", "NETFLIX", "DISNEY", "JioCinema", "News"
        ],
        "Digit Keys": [
            "Digit 0", "Digit 1", "Digit 2", "Digit 3", "Digit 4", "Digit 5",
            "Digit 6", "Digit 7", "Digit 8", "Digit 9"
        ]
    }
    
    def __init__(self, config_file: str = "key_bindings.json"):
        """
        初始化按键管理器。
        
        :param config_file: 配置文件名，默认为 key_bindings.json
        """
        self.config_file_name = config_file
        self.config_dir = self._get_config_dir()
        self.config_file = os.path.join(self.config_dir, config_file)
        self.config_data = {}
        
    def _get_config_dir(self) -> str:
        """
        获取配置文件所在目录。
        如果 config 文件夹不存在，则创建它。
        
        :return: config 文件夹的绝对路径
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(script_dir, 'config')
        
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            
        return config_dir
        
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        保存配置到文件。
        
        :param config: 配置字典
        :return: 是否保存成功
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving key config: {e}")
            return False
    
    def load_config(self) -> Optional[Dict[str, Any]]:
        """
        从文件加载配置。
        
        :return: 配置字典，如果加载失败返回 None
        """
        try:
            if not os.path.exists(self.config_file):
                return None
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
            return self.config_data
        except Exception as e:
            print(f"Error loading key config: {e}")
            return None
    
    def config_exists(self) -> bool:
        """
        检查配置文件是否存在。
        
        :return: 配置文件是否存在
        """
        return os.path.exists(self.config_file)
    
    def delete_config(self) -> bool:
        """
        删除配置文件。
        
        :return: 是否删除成功
        """
        try:
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
            return True
        except Exception as e:
            print(f"Error deleting key config: {e}")
            return False
    
    def get_config_file_path(self) -> str:
        """
        获取配置文件的完整路径。
        
        :return: 配置文件的绝对路径
        """
        return os.path.abspath(self.config_file)
    
    def get_all_keys(self) -> Dict[str, List[str]]:
        """
        获取所有按键（内置按键 + 自定义按键）。
        
        :return: 按键字典，按分类组织
        """
        config = self.load_config()
        all_keys = {}
        
        # 添加内置按键
        for category, keys in self.BUILTIN_KEYS.items():
            all_keys[category] = keys.copy()
        
        # 添加自定义按键（如果有）
        if config and 'custom_keys' in config:
            for category, keys in config['custom_keys'].items():
                if category not in all_keys:
                    all_keys[category] = []
                all_keys[category].extend(keys)
        
        return all_keys
    
    def add_custom_key(self, category: str, key_name: str) -> bool:
        """
        添加自定义按键。
        
        :param category: 按键分类
        :param key_name: 按键名称
        :return: 是否添加成功
        """
        config = self.load_config()
        if config is None:
            config = {}
        
        if 'custom_keys' not in config:
            config['custom_keys'] = {}
        
        if category not in config['custom_keys']:
            config['custom_keys'][category] = []
        
        if key_name not in config['custom_keys'][category]:
            config['custom_keys'][category].append(key_name)
            return self.save_config(config)
        
        return False
    
    def get_bindings(self) -> List[Dict[str, Any]]:
        """
        获取所有按键绑定。
        
        :return: 按键绑定列表
        """
        config = self.load_config()
        if config and 'bindings' in config:
            return config['bindings']
        return []
    
    def add_binding(self, key_name: str, x_pulse: int, y_pulse: int) -> bool:
        """
        添加按键绑定。
        
        :param key_name: 按键名称
        :param x_pulse: X轴脉冲数
        :param y_pulse: Y轴脉冲数
        :return: 是否添加成功
        """
        config = self.load_config()
        if config is None:
            config = {}
        
        if 'bindings' not in config:
            config['bindings'] = []
        
        binding = {
            'key_name': key_name,
            'x_pulse': x_pulse,
            'y_pulse': y_pulse
        }
        
        config['bindings'].append(binding)
        return self.save_config(config)
    
    def remove_binding(self, key_name: str) -> bool:
        """
        删除按键绑定。
        
        :param key_name: 按键名称
        :return: 是否删除成功
        """
        config = self.load_config()
        if config and 'bindings' in config:
            config['bindings'] = [b for b in config['bindings'] if b['key_name'] != key_name]
            return self.save_config(config)
        return False
    
    def update_binding(self, key_name: str, x_pulse: int, y_pulse: int) -> bool:
        """
        更新按键绑定。
        
        :param key_name: 按键名称
        :param x_pulse: X轴脉冲数
        :param y_pulse: Y轴脉冲数
        :return: 是否更新成功
        """
        config = self.load_config()
        if config and 'bindings' in config:
            for binding in config['bindings']:
                if binding['key_name'] == key_name:
                    binding['x_pulse'] = x_pulse
                    binding['y_pulse'] = y_pulse
                    return self.save_config(config)
        return False
    
    def clear_bindings(self) -> bool:
        """
        清空所有按键绑定。
        
        :return: 是否清空成功
        """
        config = self.load_config()
        if config is None:
            config = {}
        
        config['bindings'] = []
        return self.save_config(config)
