import json
import os
from typing import Dict, Any, Optional

class ConfigManager:
    """
    ConfigManager 类：配置管理器，负责配置的持久化存储和加载。
    使用 JSON 格式保存配置文件到本地。
    配置文件保存在程序所在目录下的 config 文件夹中。
    """
    
    def __init__(self, config_file: str = "jigctrl_config.json"):
        """
        初始化配置管理器。
        
        :param config_file: 配置文件名，默认为 jigctrl_config.json
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
        # 获取当前脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(script_dir, 'config')
        
        # 如果 config 文件夹不存在，则创建
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
            print(f"Error saving config: {e}")
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
            print(f"Error loading config: {e}")
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
            print(f"Error deleting config: {e}")
            return False
    
    def get_config_file_path(self) -> str:
        """
        获取配置文件的完整路径。
        
        :return: 配置文件的绝对路径
        """
        return os.path.abspath(self.config_file)
