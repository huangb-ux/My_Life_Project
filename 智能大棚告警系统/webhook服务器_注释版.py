# ==============================================
# 物联网数据接收服务 (Webhook Server)
# 作用：接收MQTT Broker转发的设备数据，解析后存入MySQL数据库
# ==============================================

# 导入需要的模块（module）
from flask import Flask, request, jsonify  # Flask: 轻量级Web框架 | request: 请求对象 | jsonify: JSON响应工具
import struct  # struct: 用于二进制数据的打包(pack)和解包(unpack)
import json    # json: 处理JSON格式数据
import base64  # base64: Base64编码(encode)与解码(decode)
import pymysql # pymysql: MySQL数据库连接驱动

# 初始化(initialize) Flask应用实例
app = Flask(__name__)  # __name__: 当前模块的名字（用于确定资源路径）

# ===================== 数据库配置 (Database Configuration) =====================
# 定义MySQL数据库的连接配置字典(dictionary)
DB_CONFIG = {  # DB_CONFIG: 数据库配置字典
    "host": "127.0.0.1",      # host: 数据库服务器地址（127.0.0.1表示本地localhost）
    "user": "root",           # user: 数据库用户名
    "password": "12345678",   # password: 数据库密码
    "database": "emqx_data",  # database: 要连接的数据库名称
    "charset": "utf8mb4"      # charset: 字符集（utf8mb4支持中文和特殊符号）
}

# 建立(establish)数据库连接(connection)
db = pymysql.connect(**DB_CONFIG)  # connect: 连接数据库 | **DB_CONFIG: 展开字典为关键字参数（如host="127.0.0.1", user="root"...）
# 创建游标(cursor)对象，用于执行(execute)SQL语句
cursor = db.cursor()  # cursor: 数据库游标（用于执行SQL和获取结果）

# ===================== 解析函数 (Parse Function) =====================
def parse_device_binary(bin_data):  # parse_device_binary: 解析设备二进制数据方法 | bin_data: 二进制数据
    """
    解析接收到的二进制数据包
    
    参数(parameter):
    - bin_data: 原始的二进制字节数据（bytes类型）
    
    返回(return):
    - 包含解析后字段的字典（用于数据库入库）
    """
    # 校验(validate)数据长度是否符合预期（根据协议，应为8字节）
    if len(bin_data) != 8:  # len: 获取字节长度 | !=: 不等于
        return f"长度错误：需要8字节，实际{len(bin_data)}字节"  # return: 返回错误信息

    # 使用struct.unpack解包二进制数据
    # ">HHHBB" 格式说明(format specifier):
    # > : 大端字节序(big-endian)，网络传输常用（高位在前）
    # H : unsigned short（无符号短整型，2字节，范围0-65535）
    # B : unsigned char（无符号字符型，1字节，范围0-255）
    # 所以 ">HHHBB" = 2+2+2+1+1 = 8字节
    device_id, ts, pressure_bin, status_code, reserved = struct.unpack(">HHHBB", bin_data)  # unpack: 解包二进制数据为Python值
    
    # 将压力的二进制值还原为真实物理值（原始值*10存储，所以除以10）
    pressure = round(pressure_bin / 10.0, 1)  # round: 四舍五入 | / 10.0: 除以10.0 | 1: 保留1位小数

    # --- 打印调试信息(debug info) ---
    print("======================================")  # print: 打印输出
    print("📌 BASE64解码后的数据：")  # 输出标题
    print(f"设备ID: {device_id}")  # f-string: 格式化字符串 | device_id: 设备ID
    print(f"时间戳: {ts}")  # ts: 时间戳
    print(f"压力值: {pressure:.1f} kPa")  # .1f: 保留1位小数 | kPa: 千帕
    print(f"状态码: {status_code}")  # status_code: 状态码
    print(f"保留位: {reserved}")  # reserved: 保留位
    print("======================================\n")  # \n: 换行

    # 返回解析结果（字典格式，方便后续数据库操作）
    return {  # return: 返回字典
        "device_id": device_id,      # device_id: 设备ID
        "raw_ts": ts,                # raw_ts: 原始时间戳
        "pressure": pressure,        # pressure: 压力值
        "status_code": status_code,  # status_code: 状态码（0=正常,1=警告,2=错误,3=离线）
        "reserved": reserved         # reserved: 保留位（备用字段）
    }

# ===================== Webhook接口 (API Endpoint) =====================
# 定义路由(route)，监听(listen) /webhook/bin 路径的 POST 请求
@app.route("/webhook/bin", methods=["POST"])  # @app.route: 路由装饰器 | "/webhook/bin": URL路径 | methods=["POST"]: 只接受POST请求
def webhook_bin():  # webhook_bin: Webhook处理函数
    """
    Webhook接口函数：接收MQTT Broker转发的二进制数据
    
    数据流程(data flow):
    1. 接收POST请求 → 2. 解析JSON → 3. Base64解码 → 4. 二进制解析 → 5. 数据库入库
    """
    try:  # try: 尝试执行代码块
        # 1. 获取请求的原始数据(raw data)
        raw = request.data  # request: Flask的请求对象 | data: 请求体原始数据（bytes类型）
        
        # 2. 将原始数据解析(parse)为Python字典
        json_data = json.loads(raw)  # json.loads: 把JSON字符串转成Python字典 | loads: load string（加载字符串）

        # 3. 从JSON中提取(extract)Base64编码的payload字符串
        payload_str = json_data["payload"]  # payload: 载荷，即实际的数据内容 | json_data["payload"]: 获取payload字段
        print("收到BASE64:", payload_str)  # print: 打印输出

        # 4. 使用base64解码(decode)，还原为原始二进制字节流
        payload_bytes = base64.b64decode(payload_str)  # b64decode: Base64解码 | payload_str: Base64编码的字符串
        print("✅ 最终二进制:", payload_bytes)  # ✅: 成功标记
        print("✅ 二进制长度:", len(payload_bytes))  # len: 获取字节长度

        # 5. 调用解析函数，解析二进制数据
        result = parse_device_binary(payload_bytes)  # parse_device_binary: 调用解析函数 | payload_bytes: 二进制数据
        print("✅ 解析成功:", result)  # result: 解析结果字典

        # --- 数据库入库操作(database insert) ---
        # 定义INSERT SQL语句
        sql = """  # sql: SQL语句
        INSERT INTO device_binary  -- INSERT INTO: 插入数据到表 | device_binary: 表名
        (device_id, raw_ts, pressure, status_code, reserved)  -- 要插入的字段列表
        VALUES (%s, %s, %s, %s, %s)  -- VALUES: 值列表 | %s: 占位符（防止SQL注入攻击）
        """
        
        # 执行(execute)SQL语句
        cursor.execute(sql, (  # execute: 执行SQL | sql: SQL语句 | (..., ...): 参数元组
            result["device_id"],  # 设备ID
            result["raw_ts"],     # 原始时间戳
            result["pressure"],   # 压力值
            result["status_code"], # 状态码
            result["reserved"]    # 保留位
        ))
        
        # 提交(commit)事务(transaction)，确保数据真正写入数据库
        db.commit()  # commit: 提交事务（使更改永久生效）
        print("✅ 数据成功存入 MySQL数据库！\n")  # \n: 换行

        # 返回(response)成功信息给发送方
        return jsonify({"code": 200, "data": result})  # jsonify: 转JSON响应 | 200: HTTP成功状态码

    except Exception as e:  # except: 捕获异常 | Exception: 异常基类 | e: 异常对象
        # 如果发生错误(error)，打印错误信息并返回500状态码
        print("❌ 错误:", e)  # ❌: 错误标记 | e: 异常信息
        return jsonify({"error": str(e)}), 500  # str(e): 异常转字符串 | 500: HTTP服务器内部错误状态码

# ===================== 启动服务 (Start Server) =====================
if __name__ == "__main__":  # __name__: 模块名 | "__main__": 当模块作为主程序运行时为True
    """
    程序入口：启动Flask Web服务
    
    参数说明:
    - host="0.0.0.0": 允许外部网络访问（不仅限于本机localhost）
    - port=8888: 监听8888端口
    - debug=True: 调试模式（代码修改后自动重启，显示详细错误信息）
    """
    app.run(host="0.0.0.0", port=8888, debug=True)  # run: 启动Flask开发服务器 | host: 主机地址 | port: 端口 | debug: 调试模式