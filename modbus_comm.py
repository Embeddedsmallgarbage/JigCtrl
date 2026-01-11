import struct

class ModBusComm:
    """
    ModBusComm 类：ModBus RTU 通信模块，用于与步进电机驱动器通信。
    支持读取和写入寄存器，自动处理 CRC 校验。
    """
    
    def __init__(self, device_address=1, log_callback=None):
        """
        初始化 ModBus 通信模块。
        
        :param device_address: 设备地址，默认为 1
        :param log_callback: 日志回调函数
        """
        self.device_address = device_address
        self.log = log_callback if log_callback else lambda msg, level: None
    
    def calculate_crc(self, data):
        """
        计算 ModBus RTU 协议的 CRC16 校验码。
        使用多项式 0xA001 计算。
        
        :param data: 字节数据
        :return: CRC 校验码（低字节在前）
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
    
    def build_read_command(self, register_address, register_count=1):
        """
        构建读取寄存器命令（03 指令）。
        
        :param register_address: 寄存器地址
        :param register_count: 要读取的寄存器数量
        :return: 命令字节序列
        """
        command = bytes([
            self.device_address,
            0x03,
            (register_address >> 8) & 0xFF,
            register_address & 0xFF,
            (register_count >> 8) & 0xFF,
            register_count & 0xFF
        ])
        crc = self.calculate_crc(command)
        return command + struct.pack('<H', crc)
    
    def build_write_command(self, register_address, value):
        """
        构建写入寄存器命令（06 指令）。
        
        :param register_address: 寄存器地址
        :param value: 要写入的值
        :return: 命令字节序列
        """
        command = bytes([
            self.device_address,
            0x06,
            (register_address >> 8) & 0xFF,
            register_address & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF
        ])
        crc = self.calculate_crc(command)
        return command + struct.pack('<H', crc)
    
    def send_command(self, serial_conn, command, timeout=0.1):
        """
        发送命令到串口并接收响应。
        
        :param serial_conn: 串口连接对象
        :param command: 命令字节序列
        :param timeout: 超时时间（秒）
        :return: 响应数据，如果超时或出错返回 None
        """
        if not serial_conn or not serial_conn.is_open:
            return None
        
        try:
            serial_conn.timeout = timeout
            serial_conn.write(command)
            response = serial_conn.read(8)
            
            if len(response) == 0:
                return None
            
            return response
        except Exception as e:
            print(f"Error sending command: {e}")
            return None
    
    def set_direction(self, serial_conn, forward=True):
        """
        设置电机运行方向。
        寄存器地址：0x01
        值：1=正转，0=反转
        
        :param serial_conn: 串口连接对象
        :param forward: True=正转，False=反转
        :return: 是否成功
        """
        direction_value = 1 if forward else 0
        direction_str = "forward" if forward else "reverse"
        command = self.build_write_command(0x01, direction_value)
        response = self.send_command(serial_conn, command)
        if response is not None and response == command:
            self.log(f"Direction set to {direction_str} (Register 0x01)", "MOT")
            return True
        else:
            self.log(f"Failed to set direction to {direction_str}", "ERR")
            return False
    
    def set_speed(self, serial_conn, speed_rpm):
        """
        设置电机运行速度。
        寄存器地址：0x04
        范围：1-800 r/min
        
        :param serial_conn: 串口连接对象
        :param speed_rpm: 速度（r/min）
        :return: 是否成功
        """
        if speed_rpm < 1 or speed_rpm > 800:
            self.log(f"Speed {speed_rpm} r/min out of range (1-800)", "ERR")
            return False
        
        command = self.build_write_command(0x04, speed_rpm)
        response = self.send_command(serial_conn, command)
        if response is not None and response == command:
            self.log(f"Speed set to {speed_rpm} r/min (Register 0x04)", "MOT")
            return True
        else:
            self.log(f"Failed to set speed to {speed_rpm} r/min", "ERR")
            return False
    
    def set_revolutions(self, serial_conn, revolutions):
        """
        设置电机运行圈数。
        寄存器地址：0x06
        范围：0-65535，0=一直转动
        
        :param serial_conn: 串口连接对象
        :param revolutions: 圈数
        :return: 是否成功
        """
        if revolutions < 0 or revolutions > 65535:
            self.log(f"Revolutions {revolutions} out of range (0-65535)", "ERR")
            return False
        
        command = self.build_write_command(0x06, int(revolutions))
        response = self.send_command(serial_conn, command)
        if response is not None and response == command:
            self.log(f"Revolutions set to {revolutions} (Register 0x06)", "MOT")
            return True
        else:
            self.log(f"Failed to set revolutions to {revolutions}", "ERR")
            return False
    
    def run_motor(self, serial_conn):
        """
        运行电机。
        寄存器地址：0x02
        值：1=运行
        
        :param serial_conn: 串口连接对象
        :return: 是否成功
        """
        command = self.build_write_command(0x02, 1)
        response = self.send_command(serial_conn, command)
        return response is not None and response == command
    
    def pause_motor(self, serial_conn):
        """
        暂停电机。
        寄存器地址：0x02
        值：0=暂停
        
        :param serial_conn: 串口连接对象
        :return: 是否成功
        """
        command = self.build_write_command(0x02, 0)
        response = self.send_command(serial_conn, command)
        return response is not None and response == command
    
    def stop_motor(self, serial_conn):
        """
        停止电机。
        寄存器地址：0x03
        值：1=停止
        
        :param serial_conn: 串口连接对象
        :return: 是否成功
        """
        command = self.build_write_command(0x03, 1)
        response = self.send_command(serial_conn, command)
        return response is not None and response == command
    
    def initialize_motor(self, serial_conn, speed_rpm, revolutions, forward=True):
        """
        初始化电机参数：设置速度、圈数、方向。
        
        :param serial_conn: 串口连接对象
        :param speed_rpm: 速度（r/min）
        :param revolutions: 圈数
        :param forward: True=正转，False=反转
        :return: 是否成功
        """
        if not self.set_speed(serial_conn, speed_rpm):
            return False
        
        if not self.set_revolutions(serial_conn, revolutions):
            return False
        
        if not self.set_direction(serial_conn, forward):
            return False
        
        return True
    
    def read_speed(self, serial_conn):
        """
        读取当前速度设置。
        寄存器地址：0x04
        
        :param serial_conn: 串口连接对象
        :return: 速度值，失败返回 None
        """
        command = self.build_read_command(0x04, 1)
        response = self.send_command(serial_conn, command)
        
        if response and len(response) >= 7:
            return (response[3] << 8) | response[4]
        return None
    
    def read_direction(self, serial_conn):
        """
        读取当前方向设置。
        寄存器地址：0x01
        
        :param serial_conn: 串口连接对象
        :return: 1=正转，0=反转，失败返回 None
        """
        command = self.build_read_command(0x01, 1)
        response = self.send_command(serial_conn, command)
        
        if response and len(response) >= 7:
            return (response[3] << 8) | response[4]
        return None
