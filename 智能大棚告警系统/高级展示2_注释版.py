# ==============================================
# 设备数据高级监控面板 - 注释版
# Advanced Device Data Monitoring Panel - Commented Version
# ==============================================

# 导入系统模块 (import: 导入, sys: 系统模块)
import sys
# 导入随机数模块 (random: 随机)
import random
# 导入MySQL数据库驱动 (pymysql: Python MySQL驱动)
import pymysql

# 导入数据可视化库 (matplotlib: 数据可视化库)
import matplotlib
# 设置matplotlib后端为非交互式 (use: 使用, Agg: 无GUI后端)
matplotlib.use('Agg')
# 导入pyplot子模块 (plt: 绘图接口)
import matplotlib.pyplot as plt
# 导入Qt后端画布 (FigureCanvasQTAgg: Qt图形画布)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
# 导入字体管理 (FontProperties: 字体属性)
from matplotlib.font_manager import FontProperties

# 导入日期时间模块 (datetime: 日期时间)
from datetime import datetime
# 导入数值计算库 (numpy: 数值计算)
import numpy as np

# 从PyQt6导入窗口组件 (PyQt6: Qt6的Python绑定)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QLabel, QHeaderView, QHBoxLayout,
    QPushButton, QDialog, QLineEdit, QMessageBox, QProgressBar,
    QComboBox, QToolBar, QFileDialog, QTabWidget
)
# 从PyQt6导入核心模块 (Qt: Qt框架常量, pyqtSignal: 信号, QObject: 对象基类)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
# 从PyQt6导入图形模块 (QColor: 颜色, QFont: 字体, QIcon: 图标)
from PyQt6.QtGui import QColor, QFont, QIcon

# 设置matplotlib中文字体 (rcParams: 运行时参数)
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
# 解决负号显示问题
plt.rcParams['axes.unicode_minus'] = False

# ==============================================
# 数据库默认配置 (DEFAULT_CONFIG: 默认配置)
# ==============================================
DEFAULT_CONFIG = {
    "host": "127.0.0.1",      # host: 主机地址
    "port": 3307,              # port: 端口号
    "user": "root",            # user: 用户名
    "password": "12345678",    # password: 密码
    "database": "emqx_data",   # database: 数据库名
    "charset": "utf8mb4"       # charset: 字符集
}

# ==============================================
# 信号总线类 (SignalBus: 信号总线)
# 用于跨线程通信 (pyqtSignal: 信号, QObject: Qt对象)
# ==============================================
class SignalBus(QObject):
    # 定义数据加载完成信号 (data_loaded: 数据已加载)
    data_loaded = pyqtSignal(list)  # list: 列表类型

# 创建信号总线实例 (signals: 信号)
signals = SignalBus() 

# ==============================================
# 登录对话框类 (LoginDialog: 登录对话框)
# 用于输入数据库连接IP地址
# ==============================================
class LoginDialog(QDialog):
    # 构造函数 (__init__: 初始化方法)
    def __init__(self, parent=None):
        super().__init__(parent)  # parent: 父窗口
        # 设置窗口标题 (setWindowTitle: 设置窗口标题)
        self.setWindowTitle("数据库连接配置")
        # 设置窗口大小 (resize: 调整大小)
        self.resize(300, 150)
        
        # 创建垂直布局 (QVBoxLayout: 垂直布局)
        layout = QVBoxLayout()
        
        # 创建标签 (QLabel: 标签控件)
        self.label = QLabel("请输入数据库 IP 地址:")
        # 创建输入框 (QLineEdit: 单行文本框)
        self.ip_input = QLineEdit(DEFAULT_CONFIG['host'])
        # 创建按钮 (QPushButton: 按钮)
        self.btn_connect = QPushButton("连接数据库")
        
        # 将控件添加到布局 (addWidget: 添加控件)
        layout.addWidget(self.label)
        layout.addWidget(self.ip_input)
        layout.addWidget(self.btn_connect)
        
        # 设置布局 (setLayout: 设置布局)
        self.setLayout(layout)
        
        # 绑定按钮点击事件 (clicked: 点击信号, connect: 连接)
        self.btn_connect.clicked.connect(self.accept)

    # 获取输入的IP地址 (get_ip: 获取IP)
    def get_ip(self):
        # 返回输入框文本 (text: 获取文本)
        return self.ip_input.text()

# ==============================================
# 高级监控面板主类 (AdvancedViewer: 高级查看器)
# 继承自QMainWindow (QMainWindow: 主窗口类)
# ==============================================
class AdvancedViewer(QMainWindow):
    # 构造函数
    def __init__(self, db_config):
        super().__init__()
        # db_config: 数据库配置 (database configuration)
        self.db_config = db_config
        # connection: 数据库连接对象 (database connection)
        self.connection = None
        
        # 设置窗口标题
        self.setWindowTitle("设备数据高级监控面板")
        # 设置窗口大小
        self.resize(1200, 800)
        
        # 分页相关变量 (pagination: 分页)
        self.current_page = 1    # current_page: 当前页码
        self.page_size = 10      # page_size: 每页条数
        self.total_pages = 1     # total_pages: 总页数
        
        # 初始化UI (init_ui: 初始化用户界面)
        self.init_ui()
        # 连接数据库 (connect_db: 连接数据库)
        self.connect_db()
        # 加载数据 (load_data: 加载数据)
        self.load_data()

    # ==============================================
    # 初始化用户界面 (init_ui: initialize user interface)
    # ==============================================
    def init_ui(self):
        # 设置样式表 (setStyleSheet: 设置样式表)
        self.setStyleSheet("""
            QMainWindow { background-color: #f0f2f5; }
            QTableWidget {
                background-color: white;
                gridline-color: #e0e0e0;
                font-size: 13px;
                selection-background-color: #a8dadc;
            }
            QTableWidget::item { padding: 5px; }
            QHeaderView::section {
                background-color: #4a90e2;
                color: white;
                padding: 8px;
                border: 1px solid #357abd;
                font-weight: bold;
            }
            QPushButton {
                border: 1px solid #ccc;
                padding: 4px 10px;
                border-radius: 4px;
                background-color: #fff;
            }
            QPushButton:hover { background-color: #f0f0f0; }
            QLabel { color: #333; }
            QToolBar { border: 0px; background: white; padding: 5px; }
        """)

        # 创建中央部件 (central_widget: 中央部件)
        central_widget = QWidget()
        # 设置中央部件 (setCentralWidget: 设置中央部件)
        self.setCentralWidget(central_widget)
        # 创建主布局 (main_layout: 主布局)
        main_layout = QVBoxLayout(central_widget)

        # 创建工具栏 (toolbar: 工具栏)
        toolbar = QToolBar("工具栏")
        # 添加工具栏 (addToolBar: 添加工具栏)
        self.addToolBar(toolbar)
        
        # 创建功能按钮
        self.btn_refresh = QPushButton("刷新数据")     # btn_refresh: 刷新按钮
        self.btn_export = QPushButton("导出数据")       # btn_export: 导出按钮
        self.btn_del = QPushButton("删除选中")          # btn_del: 删除按钮
        self.btn_auto_width = QPushButton("自动调整列宽") # btn_auto_width: 自动列宽按钮
        self.btn_line_chart = QPushButton("折线图")     # btn_line_chart: 折线图按钮
        self.btn_pie_chart = QPushButton("圆饼图")      # btn_pie_chart: 圆饼图按钮
        self.btn_bar_chart = QPushButton("圆柱图")      # btn_bar_chart: 柱状图按钮
        
        # 将按钮添加到工具栏
        toolbar.addWidget(self.btn_refresh)
        toolbar.addWidget(self.btn_export)
        toolbar.addWidget(self.btn_del)
        toolbar.addSeparator()  # addSeparator: 添加分隔线
        toolbar.addWidget(self.btn_auto_width)
        toolbar.addSeparator()
        toolbar.addWidget(self.btn_line_chart)
        toolbar.addWidget(self.btn_pie_chart)
        toolbar.addWidget(self.btn_bar_chart)
        
        # 创建搜索布局 (search_layout: 搜索布局)
        search_layout = QHBoxLayout()
        # 创建搜索输入框 (search_input: 搜索输入框)
        self.search_input = QLineEdit()
        # 设置占位符文本 (setPlaceholderText: 设置占位符)
        self.search_input.setPlaceholderText("搜索...")
        # 创建搜索按钮 (btn_search: 搜索按钮)
        self.btn_search = QPushButton("搜索")
        # 创建下拉列表 (cb_col: 列选择组合框)
        self.cb_col = QComboBox()
        # 添加选项 (addItems: 添加项目)
        self.cb_col.addItems(["全部列", "设备ID", "数据类型"])
        
        # 将搜索控件添加到布局
        search_layout.addWidget(QLabel("搜索列:"))
        search_layout.addWidget(self.cb_col)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.btn_search)
        # 将搜索布局添加到主布局
        main_layout.addLayout(search_layout)

        # 创建表格控件 (table: 表格)
        self.table = QTableWidget()
        # 设置列数 (setColumnCount: 设置列数)
        self.table.setColumnCount(8)
        # 设置表头标签 (setHorizontalHeaderLabels: 设置水平表头标签)
        self.table.setHorizontalHeaderLabels(["ID", "名称", "状态", "进度", "优先级", "数值", "日期", "操作"])
        
        # 获取表头 (header: 表头)
        header = self.table.horizontalHeader()
        # 设置第一列固定宽度 (ResizeMode.Fixed: 固定模式)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 50)
        # 设置第二列自适应宽度 (ResizeMode.Stretch: 拉伸模式)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        # 设置最后一列固定宽度
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(7, 80)

        # 隐藏垂直表头 (verticalHeader: 垂直表头, setVisible: 设置可见性)
        self.table.verticalHeader().setVisible(False)
        # 设置交替行颜色 (setAlternatingRowColors: 设置交替行颜色)
        self.table.setAlternatingRowColors(True)
        # 设置表格不可编辑 (EditTrigger.NoEditTriggers: 无编辑触发)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # 将表格添加到主布局
        main_layout.addWidget(self.table)

        # 设置状态栏消息 (statusBar: 状态栏, showMessage: 显示消息)
        self.statusBar().showMessage("就绪")

        # 绑定按钮事件 (信号与槽连接)
        self.btn_refresh.clicked.connect(self.load_data)           # 刷新数据
        self.btn_auto_width.clicked.connect(self.table.resizeColumnsToContents)  # 自动调整列宽
        self.btn_export.clicked.connect(self.export_data)          # 导出数据
        self.btn_line_chart.clicked.connect(self.show_line_chart)  # 显示折线图
        self.btn_pie_chart.clicked.connect(self.show_pie_chart)    # 显示圆饼图
        self.btn_bar_chart.clicked.connect(self.show_bar_chart)    # 显示柱状图
        signals.data_loaded.connect(self.update_table)             # 数据加载完成更新表格
        
        self.btn_del.clicked.connect(self.delete_selected)         # 删除选中
        self.btn_search.clicked.connect(self.search_data)          # 搜索数据
        self.search_input.returnPressed.connect(self.search_data)  # 回车键搜索
        
        # ==============================================
        # 创建分页控件 (pagination: 分页)
        # ==============================================
        pagination_layout = QHBoxLayout()  # pagination_layout: 分页布局
        self.btn_prev = QPushButton("上一页")  # btn_prev: 上一页按钮
        self.btn_next = QPushButton("下一页")  # btn_next: 下一页按钮
        self.page_label = QLabel("第 1 页 / 共 1 页")  # page_label: 页码标签
        # 初始禁用按钮 (setEnabled: 设置启用状态)
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)
        
        # 将分页控件添加到布局
        pagination_layout.addWidget(self.btn_prev)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.btn_next)
        pagination_layout.addStretch()  # addStretch: 添加拉伸空间
        
        # 将分页布局添加到主布局
        main_layout.addLayout(pagination_layout)
        
        # 绑定分页按钮事件
        self.btn_prev.clicked.connect(self.prev_page)  # 上一页
        self.btn_next.clicked.connect(self.next_page)  # 下一页

    # ==============================================
    # 连接数据库 (connect_db: connect database)
    # ==============================================
    def connect_db(self):
        try:
            # 建立数据库连接 (pymysql.connect: 连接数据库)
            self.connection = pymysql.connect(**self.db_config)
            # 更新状态栏消息
            self.statusBar().showMessage(f"已连接数据库: {self.db_config['host']}")
        except Exception as e:
            # 显示错误消息框 (QMessageBox.critical: 关键错误消息)
            QMessageBox.critical(self, "错误", f"无法连接数据库:\n{str(e)}")
            # 退出程序 (sys.exit: 退出)
            sys.exit(1)

    # ==============================================
    # 加载数据 (load_data: load data)
    # page: 页码参数 (可选)
    # ==============================================
    def load_data(self, page=None):
        # 检查数据库连接是否存在
        if not self.connection:
            return
        
        # 如果指定了页码，则更新当前页码
        if page is not None:
            self.current_page = page
        
        try:
            # 创建游标 (cursor: 游标, 用于执行SQL)
            with self.connection.cursor() as cursor:
                # 计算偏移量 (offset: 偏移量)
                offset = (self.current_page - 1) * self.page_size
                # SQL查询语句 (sql: 结构化查询语言)
                sql = """
                SELECT id, device_id, created_at, pressure, status_code, raw_ts 
                FROM device_binary 
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
                """
                # 执行SQL (execute: 执行)
                cursor.execute(sql, (self.page_size, offset))
                # 获取查询结果 (fetchall: 获取所有结果)
                results = cursor.fetchall()
                # 发送数据加载完成信号
                signals.data_loaded.emit(results)
                
                # 查询总记录数 (COUNT: 计数)
                cursor.execute("SELECT COUNT(*) FROM device_binary")
                total_count = cursor.fetchone()[0]
                # 计算总页数 (total_pages: 总页数)
                self.total_pages = (total_count + self.page_size - 1) // self.page_size
                # 更新页码标签
                self.update_page_label()
                
        except Exception as e:
            # 打印错误信息
            print(f"查询错误: {e}")
            # 显示错误消息框
            QMessageBox.critical(self, "数据库错误", f"查询数据失败:\n{str(e)}")
            return
    
    # ==============================================
    # 更新页码标签 (update_page_label: update page label)
    # ==============================================
    def update_page_label(self):
        # 更新页码显示文本
        self.page_label.setText(f"第 {self.current_page} 页 / 共 {self.total_pages} 页")
        # 根据当前页码启用/禁用按钮
        self.btn_prev.setEnabled(self.current_page > 1)           # 非第一页时启用上一页
        self.btn_next.setEnabled(self.current_page < self.total_pages)  # 非最后一页时启用下一页
    
    # ==============================================
    # 上一页 (prev_page: previous page)
    # ==============================================
    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_data()
    
    # ==============================================
    # 下一页 (next_page: next page)
    # ==============================================
    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_data()

    # ==============================================
    # 更新表格 (update_table: update table)
    # rows: 数据行列表
    # ==============================================
    def update_table(self, rows):
        # 清空表格 (setRowCount: 设置行数为0)
        self.table.setRowCount(0)
        
        # 遍历数据行 (for: 循环)
        for row_data in rows:
            # 获取当前行数 (rowCount: 行数)
            row_idx = self.table.rowCount()
            # 插入新行 (insertRow: 插入行)
            self.table.insertRow(row_idx)
            
            # 解包数据行 (unpack: 解包)
            record_id, dev_id, created_at, pressure, status_code, raw_ts = row_data
            
            # 设置ID列 (setItem: 设置单元格项)
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(record_id)))
            
            # 设置设备名称列
            name_item = QTableWidgetItem(f"设备_{dev_id}")
            # 设置字体 (setFont: 设置字体)
            name_item.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
            self.table.setItem(row_idx, 1, name_item)
            
            # 设置状态列 (status_code: 状态码)
            status_item = QTableWidgetItem()
            if status_code == 0:
                status_item.setText("正常")
                status_item.setBackground(QColor("#D4EDDA"))  # 绿色背景
                status_item.setForeground(QColor("#155724"))  # 绿色文字
            elif status_code == 1:
                status_item.setText("警告")
                status_item.setBackground(QColor("#FFF3CD"))  # 黄色背景
                status_item.setForeground(QColor("#856404"))  # 黄色文字
            else:
                status_item.setText("错误")
                status_item.setBackground(QColor("#F8D7DA"))  # 红色背景
                status_item.setForeground(QColor("#721C24"))  # 红色文字
            self.table.setItem(row_idx, 2, status_item)
            
            # 设置进度条列 (progress_bar: 进度条)
            progress_val = min(int((pressure / 200) * 100), 100) if pressure else 0
            progress_bar = QProgressBar()
            progress_bar.setValue(progress_val)
            progress_bar.setFormat(f"{pressure} kPa")
            progress_bar.setTextVisible(True)
            progress_bar.setFixedHeight(15)
            # 设置单元格控件 (setCellWidget: 设置单元格控件)
            self.table.setCellWidget(row_idx, 3, progress_bar)
            
            # 设置优先级列 (priority: 优先级)
            prio_item = QTableWidgetItem("中")
            if status_code != 0:
                prio_item.setText("高")
                prio_item.setForeground(QColor("red"))
            else:
                prio_item.setForeground(QColor("green"))
            self.table.setItem(row_idx, 4, prio_item)
            
            # 设置原始时间戳列 (raw_ts: 原始时间戳)
            self.table.setItem(row_idx, 5, QTableWidgetItem(f"{raw_ts}"))
            
            # 设置日期列 (created_at: 创建时间)
            date_str = created_at.strftime("%m-%d %H:%M") if created_at else ""
            self.table.setItem(row_idx, 6, QTableWidgetItem(date_str))
            
            # 设置操作按钮列
            btn = QPushButton("详情")
            btn.setFixedSize(60, 25)
            # 绑定按钮点击事件 (lambda: 匿名函数)
            btn.clicked.connect(lambda checked, r=row_idx: self.on_action(r))
            self.table.setCellWidget(row_idx, 7, btn)
        
        # 更新状态栏消息
        self.statusBar().showMessage(f"加载了 {len(rows)} 条记录")

    # ==============================================
    # 操作按钮点击事件 (on_action: on action)
    # row: 行索引
    # ==============================================
    def on_action(self, row):
        # 获取设备名称
        item = self.table.item(row, 1)
        name = item.text() if item else "未知"
        # 显示消息框 (QMessageBox.information: 信息消息)
        QMessageBox.information(self, "操作", f"你点击了第 {row+1} 行的操作按钮\n设备: {name}")
        
    # ==============================================
    # 导出数据 (export_data: export data)
    # ==============================================
    def export_data(self):
        # 设置对话框选项 (QFileDialog.Option.DontUseNativeDialog: 不使用本地对话框)
        options = QFileDialog.Option.DontUseNativeDialog
        # 获取保存文件名 (getSaveFileName: 获取保存文件名)
        fileName, _ = QFileDialog.getSaveFileName(self, "导出数据", "", "CSV Files (*.csv)", options=options)
        if fileName:
            # 显示导出成功消息
            QMessageBox.information(self, "导出", f"数据已模拟导出到:\n{fileName}")

    # ==============================================
    # 删除选中记录 (delete_selected: delete selected)
    # ==============================================
    def delete_selected(self):
        # 获取选中项 (selectedItems: 获取选中项)
        selected_items = self.table.selectedItems()
        if not selected_items:
            # 显示警告消息 (QMessageBox.warning: 警告消息)
            QMessageBox.warning(self, "警告", "请先选择要删除的行")
            return
        
        # 获取选中行索引 (set: 集合, 去重)
        selected_rows = set()
        for item in selected_items:
            selected_rows.add(item.row())
        
        # 收集要删除的记录ID
        delete_ids = []
        for row in selected_rows:
            id_item = self.table.item(row, 0)
            if id_item:
                delete_ids.append(int(id_item.text()))
        
        # 显示确认对话框 (QMessageBox.question: 询问消息)
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要删除选中的 {len(selected_rows)} 条记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 如果有数据库连接且有要删除的ID
                if self.connection and delete_ids:
                    with self.connection.cursor() as cursor:
                        # 构建占位符字符串
                        placeholders = ','.join(['%s'] * len(delete_ids))
                        # SQL删除语句
                        sql = f"DELETE FROM device_binary WHERE id IN ({placeholders})"
                        cursor.execute(sql, tuple(delete_ids))
                        # 提交事务 (commit: 提交)
                        self.connection.commit()
                
                # 从表格中删除行 (逆序删除避免索引错乱)
                for row in sorted(selected_rows, reverse=True):
                    self.table.removeRow(row)
                
                # 更新状态栏
                self.statusBar().showMessage(f"已删除 {len(selected_rows)} 条记录")
                
            except Exception as e:
                # 显示删除失败消息
                QMessageBox.critical(self, "删除失败", f"删除记录时发生错误:\n{str(e)}")
                try:
                    # 回滚事务 (rollback: 回滚)
                    self.connection.rollback()
                except:
                    pass

    # ==============================================
    # 搜索数据 (search_data: search data)
    # ==============================================
    def search_data(self):
        # 获取搜索文本 (strip: 去除首尾空格)
        search_text = self.search_input.text().strip()
        # 如果搜索文本为空，重新加载全部数据
        if not search_text:
            self.load_data()
            return
        
        # 获取搜索列索引 (currentIndex: 当前索引)
        search_column = self.cb_col.currentIndex()
        
        # 遍历表格行
        for row in range(self.table.rowCount()):
            match = False
            # 搜索全部列
            if search_column == 0:
                for col in range(self.table.columnCount() - 1):
                    item = self.table.item(row, col)
                    if item and search_text.lower() in item.text().lower():
                        match = True
                        break
            # 搜索设备ID列
            elif search_column == 1:
                item = self.table.item(row, 1)
                if item and search_text.lower() in item.text().lower():
                    match = True
            # 搜索状态列
            elif search_column == 2:
                item = self.table.item(row, 2)
                if item and search_text.lower() in item.text().lower():
                    match = True
            
            # 设置行可见性 (setRowHidden: 设置行隐藏)
            self.table.setRowHidden(row, not match)
        
        # 统计可见行数
        visible_rows = sum(1 for row in range(self.table.rowCount()) if not self.table.isRowHidden(row))
        # 更新状态栏
        self.statusBar().showMessage(f"搜索完成，找到 {visible_rows} 条匹配记录")

    # ==============================================
    # 获取图表数据 (get_chart_data: get chart data)
    # ==============================================
    def get_chart_data(self):
        if not self.connection:
            return []
        
        try:
            with self.connection.cursor() as cursor:
                sql = """
                SELECT created_at, pressure, status_code 
                FROM device_binary 
                ORDER BY created_at DESC 
                LIMIT 50
                """
                cursor.execute(sql)
                return cursor.fetchall()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取图表数据失败:\n{str(e)}")
            return []

    # ==============================================
    # 显示折线图 (show_line_chart: show line chart)
    # ==============================================
    def show_line_chart(self):
        # 获取图表数据
        data = self.get_chart_data()
        if not data:
            QMessageBox.warning(self, "警告", "没有可显示的数据")
            return
        
        # 创建对话框 (QDialog: 对话框)
        dialog = QDialog(self)
        dialog.setWindowTitle("压力趋势折线图")
        dialog.resize(900, 600)
        
        # 创建布局
        layout = QVBoxLayout(dialog)
        
        # 创建图表 (fig: 图形, ax: 坐标轴)
        fig, ax = plt.subplots(figsize=(12, 6))
        # 提取日期和压力数据
        dates = [row[0].strftime('%m-%d %H:%M') if row[0] else '' for row in data]
        pressures = [row[1] if row[1] is not None else 0 for row in data]
        
        # 创建X轴位置
        x_positions = range(len(dates))
        # 绘制折线图 (plot: 绘制)
        ax.plot(x_positions, pressures, marker='o', linewidth=2, markersize=6, color='#4a90e2')
        
        # 设置标签和标题 (set_xlabel: 设置X轴标签, set_ylabel: 设置Y轴标签, set_title: 设置标题)
        ax.set_xlabel('时间', fontsize=14, fontweight='bold')
        ax.set_ylabel('压力 (kPa)', fontsize=14, fontweight='bold')
        ax.set_title('设备压力趋势图', fontsize=16, fontweight='bold')
        # 设置网格 (grid: 网格)
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # 设置X轴刻度
        ax.set_xticks(x_positions[::max(1, len(dates)//10)])
        ax.set_xticklabels([dates[i] for i in x_positions[::max(1, len(dates)//10)]], rotation=45, fontsize=10)
        
        # 设置Y轴刻度字体大小
        for label in ax.get_yticklabels():
            label.set_fontsize(10)
        
        # 自动调整布局 (tight_layout: 紧凑布局)
        plt.tight_layout()
        
        # 创建Qt画布 (FigureCanvasQTAgg: Qt画布)
        canvas = FigureCanvasQTAgg(fig)
        layout.addWidget(canvas)
        
        # 设置对话框布局
        dialog.setLayout(layout)
        # 显示对话框 (exec: 执行对话框)
        dialog.exec()

    # ==============================================
    # 显示圆饼图 (show_pie_chart: show pie chart)
    # ==============================================
    def show_pie_chart(self):
        data = self.get_chart_data()
        if not data:
            QMessageBox.warning(self, "警告", "没有可显示的数据")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("状态分布圆饼图")
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # 状态映射 (status_map: 状态映射)
        status_map = {0: "正常", 1: "警告", 2: "错误", 3: "离线"}
        status_count = {}
        # 统计各状态数量
        for row in data:
            status = status_map.get(row[2], "未知")
            status_count[status] = status_count.get(status, 0) + 1
        
        # 创建饼图
        fig, ax = plt.subplots(figsize=(8, 8))
        labels = list(status_count.keys())
        sizes = list(status_count.values())
        colors = ['#4CAF50', '#FFC107', '#F44336', '#9E9E9E']
        
        # 绘制饼图 (pie: 饼图)
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%', 
                                          colors=colors[:len(labels)],
                                          startangle=90, explode=[0.05] * len(labels),
                                          textprops={'fontsize': 14})
        
        # 设置百分比文本样式
        for autotext in autotexts:
            autotext.set_fontsize(12)
            autotext.set_fontweight('bold')
        
        ax.set_title('设备状态分布图', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        canvas = FigureCanvasQTAgg(fig)
        layout.addWidget(canvas)
        
        dialog.setLayout(layout)
        dialog.exec()

    # ==============================================
    # 显示柱状图 (show_bar_chart: show bar chart)
    # ==============================================
    def show_bar_chart(self):
        data = self.get_chart_data()
        if not data:
            QMessageBox.warning(self, "警告", "没有可显示的数据")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("压力分布圆柱图")
        dialog.resize(900, 600)
        
        layout = QVBoxLayout(dialog)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        dates = [row[0].strftime('%H:%M') if row[0] else '' for row in data]
        pressures = [row[1] if row[1] is not None else 0 for row in data]
        
        x_positions = range(len(pressures))
        # 绘制柱状图 (bar: 柱状图)
        ax.bar(x_positions, pressures, color='#4a90e2', alpha=0.8)
        
        ax.set_xlabel('时间点', fontsize=14, fontweight='bold')
        ax.set_ylabel('压力 (kPa)', fontsize=14, fontweight='bold')
        ax.set_title('设备压力分布图', fontsize=16, fontweight='bold')
        
        ax.set_xticks(x_positions[::max(1, len(dates)//10)])
        ax.set_xticklabels([dates[i] for i in x_positions[::max(1, len(dates)//10)]], rotation=45, fontsize=10)
        
        for label in ax.get_yticklabels():
            label.set_fontsize(10)
        
        ax.grid(True, axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        canvas = FigureCanvasQTAgg(fig)
        layout.addWidget(canvas)
        
        dialog.setLayout(layout)
        dialog.exec()

# ==============================================
# 主函数 (main: 主函数)
# ==============================================
def main():
    # 创建应用程序实例 (QApplication: Qt应用程序)
    app = QApplication(sys.argv)
    
    # 创建登录对话框
    login = LoginDialog()
    # 显示登录对话框 (exec: 执行对话框)
    if login.exec() == QDialog.DialogCode.Accepted:
        # 获取输入的IP地址
        ip = login.get_ip()
        # 更新默认配置
        DEFAULT_CONFIG['host'] = ip
        
        # 创建主窗口实例
        window = AdvancedViewer(DEFAULT_CONFIG)
        # 显示主窗口 (show: 显示窗口)
        window.show()
        # 运行应用程序事件循环 (exec: 执行事件循环)
        sys.exit(app.exec())
    else:
        # 用户取消登录，退出程序
        sys.exit()

# ==============================================
# 程序入口 (if __name__ == "__main__": 程序入口)
# ==============================================
if __name__ == "__main__":
    main()

# ==============================================
# 代码说明 (Code Explanation)
# ==============================================
# 1. 功能概述 (Function Overview)
#    - 设备数据高级监控面板，用于展示从MySQL数据库获取的设备数据
#    - 支持数据分页、搜索、删除、导出等功能
#    - 支持折线图、圆饼图、柱状图三种数据可视化方式

# 2. 主要类 (Main Classes)
#    - SignalBus: 信号总线，用于线程间通信
#    - LoginDialog: 登录对话框，用于输入数据库IP
#    - AdvancedViewer: 主窗口类，包含所有核心功能

# 3. 核心功能 (Core Functions)
#    - init_ui(): 初始化用户界面
#    - connect_db(): 连接数据库
#    - load_data(): 加载数据（支持分页）
#    - update_table(): 更新表格显示
#    - delete_selected(): 删除选中记录
#    - search_data(): 搜索数据
#    - show_line_chart/show_pie_chart/show_bar_chart(): 显示图表

# 4. 技术栈 (Technology Stack)
#    - Python: 编程语言 (Programming Language)
#    - PyQt6: GUI框架 (GUI Framework)
#    - Matplotlib: 数据可视化库 (Data Visualization Library)
#    - PyMySQL: MySQL数据库驱动 (MySQL Database Driver)
