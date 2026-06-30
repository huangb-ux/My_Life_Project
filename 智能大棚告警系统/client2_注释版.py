# ==============================================
# MQTT设备模拟器 (MQTT Device Simulator)
# 作用：模拟物联网设备，周期性发送传感器数据到MQTT Broker
# ==============================================

# 导入需要的模块
import sys  # sys: 系统相关功能模块
sys.stdout.reconfigure(encoding='utf-8')  # reconfigure: 重新配置 | encoding: 编码 | utf-8: UTF-8编码（支持中文）
sys.stderr.reconfigure(encoding='utf-8')  # stderr: 标准错误输出

import paho.mqtt.client as mqtt  # paho.mqtt.client: MQTT客户端库 | mqtt: 别名
import random  # random: 随机数生成模块
import time    # time: 时间相关功能模块
import json    # json: JSON数据处理模块
import struct  # struct: 二进制数据打包/解包模块
import logging # logging: 日志记录模块
import base64  # base64: Base64编解码模块
import pymysql # pymysql: MySQL数据库连接驱动
from datetime import datetime  # datetime: 日期时间处理类
from threading import Timer    # Timer: 定时器类（用于定时任务）
from uuid import uuid4         # uuid4: UUID生成器（生成唯一标识符）

# 强制Python使用UTF-8编码输出（确保兼容性）
sys.stdout.reconfigure(encoding='utf-8')  # stdout: 标准输出 | reconfigure: 重新配置
sys.stderr.reconfigure(encoding='utf-8')  # stderr: 标准错误输出

# ===================== 配置区 (Configuration) =====================
CONFIG = {  # CONFIG: 配置字典（存储所有配置参数）
    "device_id": "device_001",     # device_id: 设备唯一标识符
    "mqtt_host": "172.24.29.145", # mqtt_host: MQTT Broker服务器地址
    "mqtt_port": 1883,             # mqtt_port: MQTT Broker端口（默认1883）
    "mqtt_username": "haung",      # mqtt_username: MQTT用户名
    "mqtt_password": "1",          # mqtt_password: MQTT密码
    "temp_humidity_interval": 60,  # temp_humidity_interval: 温湿度数据发送间隔（秒）
    "light_interval": 60,          # light_interval: 光照数据发送间隔（秒）
    "binary_interval": 60,         # binary_interval: 二进制数据发送间隔（秒）
    "topic_prefix": "topic",       # topic_prefix: MQTT主题前缀
    "db_host": "127.0.0.1",        # db_host: 数据库服务器地址（127.0.0.1表示本地）
    "db_port": 3307,               # db_port: 数据库端口号
    "db_user": "root",             # db_user: 数据库用户名
    "db_password": "12345678",     # db_password: 数据库密码
    "db_database": "emqx_data"     # db_database: 数据库名称
}

# 传感器数据范围配置
DATA_RANGES = {  # DATA_RANGES: 数据范围字典
    "temperature": (-20, 60, 1, "C"),      # temperature: 温度 | (最小值, 最大值, 小数位数, 单位)
    "humidity": (0, 100, 1, "%RH"),        # humidity: 湿度 | %RH: 相对湿度百分比
    "light": (0, 100000, 0, "lux"),        # light: 光照强度 | lux: 勒克斯（光照单位）
    "pressure": (90, 110, 1, "kPa"),       # pressure: 压力 | kPa: 千帕
    "status": ["online", "normal", "alarm", "offline"]  # status: 设备状态列表
}

# ===================== 日志配置 (Logging Configuration) =====================
logging.basicConfig(  # basicConfig: 基础日志配置
    level=logging.INFO,  # level: 日志级别（INFO表示普通信息，还有DEBUG、WARNING、ERROR、CRITICAL）
    format="%(asctime)s - %(levelname)s - %(message)s",  # format: 日志格式 | asctime: 时间 | levelname: 级别名 | message: 消息
    handlers=[  # handlers: 日志处理器列表
        logging.FileHandler("mqtt_device_simulator.log", encoding="utf-8"),  # FileHandler: 文件处理器（写入日志文件） | encoding: 编码
        logging.StreamHandler(sys.stdout)  # StreamHandler: 流处理器（输出到控制台） | sys.stdout: 标准输出
    ]
)
logger = logging.getLogger(__name__)  # getLogger: 获取日志记录器对象 | __name__: 当前模块名

# ===================== MQTT连接 (MQTT Connection) =====================
client = None  # client: MQTT客户端对象（全局变量，初始化为None）
last_values = {"temperature": 25.0, "humidity": 50.0}  # last_values: 保存上一次的温湿度值（用于平滑变化）

# ===================== 数据库操作类 (Database Handler Class) =====================
class DatabaseHandler:  # DatabaseHandler: 数据库操作类
    """
    数据库操作类：负责连接数据库、插入数据
    
    方法(method):
    - connect(): 连接数据库
    - insert_device_data(): 插入设备数据
    - close(): 关闭数据库连接
    """
    
    def __init__(self):  # __init__: 构造函数（初始化方法）
        """构造函数(Constructor)：初始化数据库连接为None"""
        self.connection = None  # connection: 数据库连接对象（初始化为None）
    
    def connect(self):  # connect: 连接数据库方法
        """连接(connect)到MySQL数据库"""
        try:  # try: 尝试执行代码块
            self.connection = pymysql.connect(  # connect: 连接数据库
                host=CONFIG["db_host"],  # host: 数据库主机地址
                port=CONFIG["db_port"],  # port: 数据库端口
                user=CONFIG["db_user"],  # user: 数据库用户名
                password=CONFIG["db_password"],  # password: 数据库密码
                database=CONFIG["db_database"],  # database: 数据库名称
                charset='utf8mb4'  # charset: 字符集（utf8mb4支持4字节UTF-8字符）
            )
            logger.info("数据库连接成功")  # info: 记录信息级别日志
            return True  # return: 返回True（表示连接成功）
        except Exception as e:  # except: 捕获异常 | Exception: 异常基类 | e: 异常对象
            logger.error(f"数据库连接失败: {str(e)}")  # error: 记录错误级别日志 | str(e): 异常信息转字符串
            return False  # return: 返回False（表示连接失败）
    
    def insert_device_data(self, device_id, data_type, topic, json_value=None, binary_value=None):  # insert_device_data: 插入设备数据方法
        """
        插入(insert)设备数据到数据库
        
        参数:
        - device_id: 设备ID
        - data_type: 数据类型（如temperature, binary）
        - topic: MQTT主题
        - json_value: JSON格式数据（可选，默认None）
        - binary_value: 二进制格式数据（可选，默认None）
        """
        # 先检查连接是否存在
        try:  # try: 尝试执行
            if not self.connection:  # 如果连接不存在
                if not self.connect():  # 尝试连接
                    return False  # 连接失败，返回False
            else:  # 如果连接存在
                self.connection.ping(reconnect=True)  # ping: 检查连接是否活跃 | reconnect=True: 断开时自动重连
        except Exception as e:  # except: 捕获异常
            logger.warning(f"数据库连接检查失败，尝试重连: {str(e)}")  # warning: 记录警告级别日志
            self.connection = None  # 重置连接为None
            if not self.connect():  # 尝试重新连接
                return False  # 连接失败，返回False
        
        # 执行插入操作
        try:  # try: 尝试执行
            with self.connection.cursor() as cursor:  # with: 上下文管理器（自动管理资源） | cursor: 数据库游标（用于执行SQL）
                sql = """  # sql: SQL语句
                INSERT INTO device_data (device_id, data_type, topic, json_value, binary_value)  # INSERT INTO: 插入数据到表
                VALUES (%s, %s, %s, %s, %s)  # VALUES: 值列表 | %s: 占位符（防止SQL注入）
                """
                cursor.execute(sql, (device_id, data_type, topic, json_value, binary_value))  # execute: 执行SQL语句
            self.connection.commit()  # commit: 提交事务（使更改生效）
            logger.info(f"数据已插入数据库 | device_id={device_id} | data_type={data_type}")  # info: 记录日志
            return True  # return: 返回True（表示插入成功）
        except Exception as e:  # except: 捕获异常
            logger.error(f"插入数据库失败: {str(e)}")  # error: 记录错误日志
            try:  # 尝试回滚
                self.connection.rollback()  # rollback: 回滚事务（撤销未提交的更改）
            except:  # 捕获所有异常（忽略）
                pass  # pass: 空语句（什么都不做）
            self.connection = None  # 重置连接为None
            return False  # return: 返回False（表示插入失败）
    
    def close(self):  # close: 关闭连接方法
        """关闭(close)数据库连接"""
        if self.connection:  # 如果连接存在
            self.connection.close()  # close: 关闭连接
            logger.info("数据库连接已关闭")  # info: 记录日志

# 创建数据库操作实例
db_handler = DatabaseHandler()  # db_handler: 数据库操作对象实例

# ===================== MQTT回调函数 (MQTT Callback Functions) =====================
def on_connect(client, userdata, flags, rc, properties=None):  # on_connect: 连接成功回调函数 | client: MQTT客户端 | userdata: 用户数据 | flags: 连接标志 | rc: 返回码 | properties: MQTT 5.0属性
    """
    MQTT连接成功回调(callback)函数
    
    参数:
    - rc: 连接结果码（0表示成功，非0表示失败）
    """
    if rc == 0:  # 如果返回码为0（连接成功）
        logger.info(f"连接成功 | 设备: {CONFIG['device_id']}")  # info: 记录日志
    else:  # 否则（连接失败）
        logger.error(f"连接失败 错误码: {rc}")  # error: 记录错误日志

def on_disconnect(client, userdata, rc, properties=None):  # on_disconnect: 断开连接回调函数
    """MQTT断开连接回调函数"""
    if rc != 0:  # 如果返回码不为0（异常断开）
        logger.warning(f"断开连接 错误码: {rc}，正在自动重连...")  # warning: 记录警告日志

# ===================== JSON数据生成 (JSON Data Generation) =====================
def generate_json_data(data_type):  # generate_json_data: 生成JSON数据方法 | data_type: 数据类型
    """
    生成(generate)JSON格式的传感器数据
    
    参数:
    - data_type: 数据类型（temperature/humidity/light/status）
    
    返回:
    - JSON格式的传感器数据字典
    """
    if data_type not in DATA_RANGES:  # 如果数据类型不在DATA_RANGES中
        return None  # return: 返回None（表示无效类型）

    if data_type == "status":  # 如果是状态类型
        value = random.choice(DATA_RANGES["status"])  # choice: 随机选择一个状态 | DATA_RANGES["status"]: 状态列表
        unit = ""  # unit: 单位（状态没有单位）
    else:  # 否则（数值类型）
        # 获取数据范围配置
        min_v, max_v, decimal, unit = DATA_RANGES[data_type]  # 解包元组（最小值, 最大值, 小数位数, 单位）
        
        if data_type in ["temperature", "humidity"]:  # 如果是温度或湿度
            # 温湿度：基于上一次值平滑变化（模拟真实传感器）
            last = last_values[data_type]  # last: 上一次的值
            delta = round(random.uniform(-0.5, 0.5), decimal)  # delta: 变化量 | uniform: 生成均匀分布随机数 | round: 四舍五入 | decimal: 小数位数
            value = round(last + delta, decimal)  # value: 新值 = 上一次值 + 变化量
            value = max(min_v, min(value, max_v))  # 限制在范围内（最小值 <= value <= 最大值）
            last_values[data_type] = value  # 更新上一次值
        else:  # 其他数据（光照等）
            # 直接生成随机值
            value = round(random.uniform(min_v, max_v), decimal)  # uniform: 生成均匀分布随机数 | round: 四舍五入

    # 返回标准格式的JSON数据
    return {  # return: 返回字典
        "deviceId": CONFIG["device_id"],  # deviceId: 设备ID
        "timestamp": int(time.time() * 1000),  # timestamp: 时间戳（毫秒） | time.time(): 当前时间戳（秒） | * 1000: 转毫秒 | int: 转整数
        "dataType": data_type,  # dataType: 数据类型
        "value": value,  # value: 数值
        "unit": unit  # unit: 单位
    }

# ===================== 二进制数据生成 (Binary Data Generation) =====================
def generate_binary_packet():  # generate_binary_packet: 生成二进制数据包方法
    """
    生成(generate)二进制格式的数据包
    
    返回:
    - bin_data: 打包后的二进制数据（8字节）
    - pressure: 压力值（浮点型，用于日志）
    - status_code: 状态码
    """
    device_id_bin = 0x0001  # device_id_bin: 设备ID（二进制，2字节，0x0001=1）
    ts = int(time.time()) & 0xFFFF  # ts: 时间戳低16位（2字节） | time.time(): 当前时间戳 | & 0xFFFF: 按位与（取低16位）
    pressure = random.uniform(90, 110)  # pressure: 压力值（90-110 kPa） | uniform: 均匀分布随机数
    pressure_bin = int(pressure * 10)  # pressure_bin: 压力值二进制（放大10倍转整数存储）
    status_code = random.randint(0, 3)  # status_code: 状态码（0=正常,1=警告,2=错误,3=离线） | randint: 随机整数
    reserved = 0  # reserved: 保留位（备用字段）
    
    # 使用struct.pack打包成二进制
    # ">HHHBB" = 大端序 + 3个无符号短整型 + 2个无符号字节 = 8字节
    # >: 大端字节序（网络字节序） | H: unsigned short（无符号短整型，2字节） | B: unsigned char（无符号字符型，1字节）
    bin_data = struct.pack(">HHHBB", device_id_bin, ts, pressure_bin, status_code, reserved)  # pack: 打包为二进制数据
    return bin_data, pressure, status_code  # return: 返回三元组（二进制数据, 压力值, 状态码）

# ===================== 发送函数 (Publish Functions) =====================
def publish_json(data_type, topic):  # publish_json: 发布JSON数据方法 | data_type: 数据类型 | topic: MQTT主题
    """
    发布(publish)JSON格式数据到MQTT Broker
    
    参数:
    - data_type: 数据类型
    - topic: MQTT主题
    """
    try:  # try: 尝试执行
        # 生成JSON数据
        data = generate_json_data(data_type)  # generate_json_data: 生成JSON数据
        payload = json.dumps(data, ensure_ascii=False)  # dumps: 转JSON字符串 | ensure_ascii=False: 不转义非ASCII字符（支持中文）
        encoded_payload = base64.b64encode(payload.encode('utf-8')).decode('ascii')  # b64encode: Base64编码 | encode: 转字节 | decode: 转字符串
        
        # 发布到MQTT
        client.publish(topic, encoded_payload, qos=0)  # publish: 发布消息 | topic: 主题 | encoded_payload: 载荷 | qos=0: 最多一次投递（不保证到达）
        logger.info(f"发送成功 | {topic} | {payload}")  # info: 记录日志
        
        # 同时存入数据库
        db_handler.insert_device_data(  # insert_device_data: 插入数据到数据库
            device_id=data["deviceId"],  # device_id: 设备ID
            data_type=data["dataType"],  # data_type: 数据类型
            topic=topic,  # topic: MQTT主题
            json_value=payload  # json_value: JSON数据
        )
    except Exception as e:  # except: 捕获异常
        logger.error(f"发送失败 | {topic} | {str(e)}")  # error: 记录错误日志

def publish_binary():  # publish_binary: 发布二进制数据方法
    """发布二进制格式数据到MQTT Broker"""
    try:  # try: 尝试执行
        # 生成二进制数据
        bin_data, pressure, status = generate_binary_packet()  # generate_binary_packet: 生成二进制数据包
        topic = f"{CONFIG['topic_prefix']}/bin/{CONFIG['device_id']}"  # topic: MQTT主题（f-string格式化）
        encoded_payload = base64.b64encode(bin_data).decode('ascii')  # b64encode: Base64编码 | decode: 转字符串
        
        # 发布到MQTT
        client.publish(topic, encoded_payload, qos=0)  # publish: 发布消息 | qos=0: 最多一次投递
        logger.info(f"二进制发送 | {topic} | 压力={pressure:.1f}kPa 状态={status}")  # info: 记录日志 | .1f: 保留1位小数
        
        # 同时存入数据库
        db_handler.insert_device_data(  # insert_device_data: 插入数据到数据库
            device_id=CONFIG["device_id"],  # device_id: 设备ID
            data_type="binary",  # data_type: 数据类型（二进制）
            topic=topic,  # topic: MQTT主题
            binary_value=bin_data  # binary_value: 二进制数据
        )
    except Exception as e:  # except: 捕获异常
        logger.error(f"二进制发送失败: {str(e)}")  # error: 记录错误日志
    
    # 定时重复执行（递归调用）
    Timer(CONFIG["binary_interval"], publish_binary).start()  # Timer: 定时器 | CONFIG["binary_interval"]: 间隔时间 | publish_binary: 回调函数 | start: 启动定时器

# ===================== 定时任务 (Scheduled Tasks) =====================
def all_in_one_task():  # all_in_one_task: 整合所有任务的定时函数
    """
    整合所有任务的定时函数
    
    每60秒执行一次，发送温度、湿度、光照和二进制数据
    """
    publish_json("temperature", f"{CONFIG['topic_prefix']}/temp/{CONFIG['device_id']}")  # 发布温度数据
    publish_json("humidity", f"{CONFIG['topic_prefix']}/moi/{CONFIG['device_id']}")  # 发布湿度数据
    publish_json("light", f"{CONFIG['topic_prefix']}/light/{CONFIG['device_id']}")  # 发布光照数据
    publish_binary()  # 发布二进制数据
    
    # 60秒后再次执行
    Timer(CONFIG["temp_humidity_interval"], all_in_one_task).start()  # Timer: 定时器 | start: 启动

# ===================== 主程序 (Main Program) =====================
def main():  # main: 主函数
    """
    主函数(main function)：程序入口
    
    流程(flow):
    1. 创建MQTT客户端
    2. 设置用户名密码
    3. 绑定回调函数
    4. 连接MQTT Broker
    5. 启动定时任务
    6. 进入MQTT消息循环
    """
    global client  # global: 声明使用全局变量
    
    # 生成唯一的客户端ID（device_id + 随机8位UUID）
    client_id = f"{CONFIG['device_id']}_{uuid4().hex[:8]}"  # uuid4(): 生成UUID4 | hex[:8]: 取前8位十六进制字符
    
    # 创建MQTT客户端实例
    client = mqtt.Client(  # Client: MQTT客户端类
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,  # callback_api_version: 回调API版本 | VERSION2: MQTT 5.0 API
        client_id=client_id,  # client_id: 客户端ID
        clean_session=True  # clean_session: 清除会话（断开后不保留订阅）
    )
    
    # 设置MQTT用户名和密码
    client.username_pw_set(CONFIG["mqtt_username"], CONFIG["mqtt_password"])  # username_pw_set: 设置用户名和密码
    
    # 绑定回调函数
    client.on_connect = on_connect  # on_connect: 连接成功回调
    client.on_disconnect = on_disconnect  # on_disconnect: 断开连接回调

    # 连接MQTT Broker
    try:  # try: 尝试执行
        client.connect(CONFIG["mqtt_host"], CONFIG["mqtt_port"], 60)  # connect: 连接服务器 | host: 主机地址 | port: 端口 | 60: 保活时间（秒）
    except Exception as e:  # except: 捕获异常
        logger.error(f"无法连接服务器: {str(e)}")  # error: 记录错误日志
        return  # return: 返回（退出函数）

    # 启动定时任务
    all_in_one_task()  # all_in_one_task: 启动定时任务
    logger.info("设备已启动，每分钟发送一条数据...")  # info: 记录日志
    
    # 进入MQTT消息循环（阻塞式）
    client.loop_forever()  # loop_forever: 永久循环（阻塞直到程序退出）

# 程序入口
if __name__ == "__main__":  # __name__: 模块名 | "__main__": 当模块作为主程序运行时为True
    main()  # main: 调用主函数