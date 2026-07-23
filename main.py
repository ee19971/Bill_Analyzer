#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ✔️to-do：添加图形化界面并打包
# ✔️to-do：添加词云
# ✔️to-do：添加图表可视化
# todo：添加汇率转换
# todo：支持记账软件的账单
# todo：支持银行app导出的账单

import os
import sys
import re
import logging
import threading
import tkinter as tk
import ctypes
import webbrowser
import pandas as pd
import matplotlib.pyplot as plt

from matplotlib.font_manager import FontProperties, fontManager
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, filedialog, ttk
from PIL import ImageFont

from cheng_xu import wx_csv, zfb_wy_csv, zfb_app_zhong_wen_csv, ci_yun
from cheng_xu.ci_yun import _detect_encoding, _read_data_file
from cheng_xu.ke_shi_hua import generate_chart_html, CHART_TYPES, get_available_years
from cheng_xu.ke_shi_hua_echarts import generate_echarts_html, ECHARTS_CHART_TYPES

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 账单类型与处理函数的映射表
BILL_PROCESSORS = {
    "微信app导出": wx_csv,
    "支付宝网页导出": zfb_wy_csv,
    "支付宝APP中文导出": zfb_app_zhong_wen_csv,
}

# 支持的账单类型列表
BILL_TYPES = list(BILL_PROCESSORS.keys())


class BillAnalyzerUI:
    """
    主窗口类，包含账单分析和词云生成功能。
    主要功能：
    - 文件选择与处理
    - 字体管理和应用
    - 账单分析结果展示
    - 词云生成与保存
    """

    def __init__(self, root):
        """初始化主窗口和相关组件

        Args:
            root: Tkinter 根窗口对象
        """
        self.root = root
        self.root.title("账单分析工具")
        self.root.geometry("800x600")

        # 获取当前工作目录（即 .exe 文件所在目录或脚本所在目录）
        self.current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

        # --- 字体相关初始化 ---
        self.font_dir = os.path.join(self.current_dir, "f_ont")
        self.default_font = "LXGWNeoXiHeiPlus.ttf"
        self.default_font_name = os.path.splitext(self.default_font)[0]
        self.size_var = tk.StringVar(value="10")
        self.file_path_var_main = tk.StringVar()
        self.file_path_var_vis = tk.StringVar()
        self.bill_type = tk.StringVar(value=BILL_TYPES[0])
        self.current_text = ""
        self.current_image = None
        self.current_wordcloud_image = None
        self.mask_image_path = tk.StringVar()

        # 验证默认字体是否存在
        if not self._validate_default_font():
            return

        # 预加载默认字体到 matplotlib
        self._setup_matplotlib_font(self.default_font)

        # 加载可用字体列表并初始化界面
        self.available_fonts = self._load_custom_fonts()
        self.create_ui_components()
        self.create_menu()

        # 分析报告导出
        self.current_text = ""
        self.current_image = None
        self.current_wordcloud_image = None
        self.mask_image_path = tk.StringVar()
        self._source_file_path = ""
        self._source_bill_type = ""

    def _setup_matplotlib_font(self, font_filename: str) -> None:
        """配置 matplotlib 使用指定字体

        Args:
            font_filename: 字体文件名（含扩展名）
        """
        font_path = os.path.join(self.font_dir, font_filename)
        fontManager.addfont(font_path)
        font_prop = FontProperties(fname=font_path)
        plt.rcParams['font.sans-serif'] = [font_prop.get_name()]
        plt.rcParams['axes.unicode_minus'] = False

    def _validate_default_font(self) -> bool:
        """验证默认字体文件是否存在

        Returns:
            bool: 字体存在返回True，否则销毁窗口并返回False
        """
        default_font_path = os.path.join(self.font_dir, self.default_font)
        if not os.path.exists(default_font_path):
            messagebox.showerror(
                "致命错误",
                f"缺失关键字体文件：{self.default_font}\n请检查 {self.font_dir} 目录。",
            )
            self.root.destroy()
            return False
        return True

    def _load_custom_fonts(self) -> list:
        """扫描字体目录，加载所有可用的 TTF/OTF 字体名称

        Returns:
            list: 字体名称列表（不含扩展名），默认字体排在首位
        """
        custom_fonts = []
        if not os.path.exists(self.font_dir):
            messagebox.showerror("错误", f"字体目录不存在: {self.font_dir}")
            return [self.default_font_name]

        for f in os.listdir(self.font_dir):
            if f.lower().endswith(('.ttf', '.otf')):
                custom_fonts.append(os.path.splitext(f)[0])

        # 确保默认字体在列表首位
        if self.default_font_name not in custom_fonts:
            custom_fonts.insert(0, self.default_font_name)

        return custom_fonts

    def _get_font_path(self, font_name: str) -> str:
        """根据字体名称查找字体文件路径

        Args:
            font_name: 字体名称（不含扩展名）

        Returns:
            str: 字体文件完整路径，未找到返回None
        """
        for ext in ['.ttf', '.otf', '.TTF', '.OTF']:
            test_path = os.path.join(self.font_dir, f"{font_name}{ext}")
            if os.path.exists(test_path):
                return test_path
        return None

    def _get_safe_filename(self, filename: str) -> str:
        """生成安全的文件名（替换Windows非法字符）

        Args:
            filename: 原始文件名

        Returns:
            str: 替换非法字符后的安全文件名
        """
        return re.sub(r'[\\/*?:"<>|]', '_', filename)

    # ======================== UI 构建 ========================

    def create_ui_components(self):
        """创建主界面UI组件（标签页容器）"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 账单分析标签页
        bill_frame = tk.Frame(self.notebook)
        self.notebook.add(bill_frame, text="账单分析")
        self._create_bill_analysis_ui(bill_frame)

        # 词云生成标签页
        wc_frame = tk.Frame(self.notebook)
        self.notebook.add(wc_frame, text="词云生成")
        self._create_word_cloud_ui(wc_frame)

        # 可视化plotly生成标签页
        vis_frame = tk.Frame(self.notebook)
        self.notebook.add(vis_frame, text="可视化-plotly")
        self._create_visualization_ui(vis_frame)

        # 可视化echarts生成标签页
        echarts_frame = tk.Frame(self.notebook)
        self.notebook.add(echarts_frame, text="可视化-echarts")
        self._create_echarts_ui(echarts_frame)

    def _create_bill_analysis_ui(self, parent):
        """创建账单分析标签页UI

        Args:
            parent: 父容器控件
        """
        # 文件路径显示
        tk.Label(parent, textvariable=self.file_path_var_main).pack(pady=10)

        # 文件选择按钮
        tk.Button(parent, text="选择文件", command=self._select_main_file).pack(pady=10)

        # 账单类型下拉框
        ttk.Combobox(
            parent,
            textvariable=self.bill_type,
            values=BILL_TYPES,
        ).pack(pady=10)

        # 运行分析按钮
        tk.Button(parent, text="运行分析", command=self._process_file).pack(pady=20)

        # 状态栏
        self.bill_status_var = tk.StringVar()
        self.bill_status_label = tk.Label(parent, textvariable=self.bill_status_var, fg="gray")
        self.bill_status_label.pack(pady=5)

        # 输出文本框（用于显示分析结果）- 使用grid布局确保滚动条稳定
        text_frame = tk.Frame(parent)
        text_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        self.output_text = tk.Text(text_frame, height=20, wrap=tk.NONE)
        self.output_text.grid(row=0, column=0, sticky='nsew')
        
        # 垂直滚动条
        self.v_scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.output_text.yview)
        self.v_scrollbar.grid(row=0, column=1, sticky='ns')
        
        # 水平滚动条
        self.h_scrollbar = tk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.output_text.xview)
        self.h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        self.output_text.config(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)
        self.output_text.config(state=tk.DISABLED)

    def _create_word_cloud_ui(self, parent):
        """创建词云生成标签页UI

        Args:
            parent: 父容器控件
        """
        # 文件路径显示
        self.file_path_var_wc = tk.StringVar()
        tk.Label(parent, textvariable=self.file_path_var_wc).pack(pady=10)

        # 文件选择按钮
        tk.Button(parent, text="选择文件", command=self._select_file_for_word_cloud).pack(pady=10)

        # 列名选择
        col_frame = tk.Frame(parent)
        col_frame.pack(pady=10)
        tk.Label(col_frame, text="选择列名:").pack(side=tk.LEFT)
        self.column_combo = ttk.Combobox(col_frame, state="readonly")
        self.column_combo.pack(side=tk.LEFT, padx=5)

        # 颜色映射选择
        cmap_frame = tk.Frame(parent)
        cmap_frame.pack(pady=10)
        tk.Label(cmap_frame, text="选择颜色映射:").pack(side=tk.LEFT)
        self.colormap_combo = ttk.Combobox(cmap_frame, state="readonly", values=self._get_colormaps())
        self.colormap_combo.current(0)
        self.colormap_combo.pack(side=tk.LEFT, padx=5)

        # 掩码图像选择
        mask_frame = tk.Frame(parent)
        mask_frame.pack(pady=10)
        tk.Button(mask_frame, text="选择掩码图", command=self._select_mask_image).pack(side=tk.LEFT)

        tk.Label(parent, textvariable=self.mask_image_path).pack(pady=5)

        # 生成词云按钮
        tk.Button(parent, text="生成词云", command=self._generate_word_cloud).pack(pady=20)

        # 保存图片按钮
        tk.Button(parent, text="保存图片", command=self._save_word_cloud_image).pack(pady=10)

        # 状态栏
        self.wc_status_var = tk.StringVar()
        self.wc_status_label = tk.Label(parent, textvariable=self.wc_status_var, fg="gray")
        self.wc_status_label.pack(pady=5)

    def _create_visualization_ui(self, parent):
        """创建可视化生成标签页UI

        Args:
            parent: 父容器控件
        """
        tk.Label(parent, textvariable=self.file_path_var_vis).pack(pady=10)

        tk.Button(parent, text="选择文件", command=self._select_file_for_visualization).pack(pady=10)

        chart_frame = tk.Frame(parent)
        chart_frame.pack(pady=10)
        tk.Label(chart_frame, text="图表类型:").pack(side=tk.LEFT)
        self.chart_type_combo = ttk.Combobox(
            chart_frame, state="readonly",
            values=list(CHART_TYPES.keys()),
            width=20,
        )
        self.chart_type_combo.current(0)
        self.chart_type_combo.pack(side=tk.LEFT, padx=5)

        year_frame = tk.Frame(parent)
        year_frame.pack(pady=10)
        tk.Label(year_frame, text="年份:").pack(side=tk.LEFT)
        self.year_combo = ttk.Combobox(year_frame, state="readonly", width=15)
        self.year_combo.pack(side=tk.LEFT, padx=5)

        self.vis_btn = tk.Button(parent, text="生成图表", command=self._generate_visualization)
        self.vis_btn.pack(pady=20)

        self.vis_status_var = tk.StringVar()
        self.vis_status_label = tk.Label(parent, textvariable=self.vis_status_var, fg="gray")
        self.vis_status_label.pack(pady=5)

    def _create_echarts_ui(self, parent):
        """创建ECharts可视化标签页UI

        Args:
            parent: 父容器控件
        """
        self.file_path_var_echarts = tk.StringVar()
        tk.Label(parent, textvariable=self.file_path_var_echarts).pack(pady=10)

        tk.Button(parent, text="选择文件", command=self._select_file_for_echarts).pack(pady=10)

        chart_frame = tk.Frame(parent)
        chart_frame.pack(pady=10)
        tk.Label(chart_frame, text="图表类型:").pack(side=tk.LEFT)
        self.echarts_type_combo = ttk.Combobox(
            chart_frame, state="readonly",
            values=list(ECHARTS_CHART_TYPES.keys()),
            width=20,
        )
        self.echarts_type_combo.current(0)
        self.echarts_type_combo.pack(side=tk.LEFT, padx=5)

        year_frame = tk.Frame(parent)
        year_frame.pack(pady=10)
        tk.Label(year_frame, text="年份:").pack(side=tk.LEFT)
        self.echarts_year_combo = ttk.Combobox(year_frame, state="readonly", width=15)
        self.echarts_year_combo.pack(side=tk.LEFT, padx=5)

        self.echarts_btn = tk.Button(parent, text="生成图表", command=self._generate_echarts)
        self.echarts_btn.pack(pady=20)

        self.echarts_status_var = tk.StringVar()
        self.echarts_status_label = tk.Label(parent, textvariable=self.echarts_status_var, fg="gray")
        self.echarts_status_label.pack(pady=5)

    def _select_file_for_echarts(self):
        """选择ECharts可视化数据源文件，并自动加载年份列表"""
        path = filedialog.askopenfilename(
            filetypes=[("CSV 文件", "*.csv"), ("Excel 文件", "*.xlsx *.xls")]
        )
        if path:
            self.file_path_var_echarts.set(f"当前文件: {path}")
            try:
                years = get_available_years(path)
                self.echarts_year_combo['values'] = [str(y) for y in years]
                if years:
                    self.echarts_year_combo.current(0)
            except Exception as e:
                messagebox.showerror("错误", f"读取年份失败: {str(e)}")

    def _generate_echarts(self):
        """根据用户选择的图表类型和年份生成ECharts HTML并打开"""
        chart_label = self.echarts_type_combo.get()
        chart_type = ECHARTS_CHART_TYPES.get(chart_label, "waterfall")

        file_path = self.file_path_var_echarts.get().split(': ')[-1]
        year_selection = self.echarts_year_combo.get()

        self.echarts_btn.config(state=tk.DISABLED)
        self.echarts_status_var.set(f"正在生成「{chart_label}」，请稍候...")
        self.echarts_status_label.config(fg="blue")

        def task():
            try:
                if not file_path:
                    raise ValueError("未选择文件")

                year_param = int(year_selection) if year_selection else None

                output_dir = self.current_dir
                html_path = generate_echarts_html(file_path, output_dir, chart_type,
                                                  year=year_param)

                self.root.after(0, lambda: self._on_echarts_done(html_path, chart_label))
            except Exception as e:
                self.root.after(0, lambda e=e: self._on_echarts_error(str(e)))

        threading.Thread(target=task, daemon=True).start()

    def _on_echarts_done(self, html_path: str, chart_label: str):
        """ECharts生成完成后的回调"""
        self.echarts_btn.config(state=tk.NORMAL)
        self.echarts_status_var.set(f"✓ 「{chart_label}」已保存至：{html_path}")
        self.echarts_status_label.config(fg="green")
        webbrowser.open(Path(html_path).as_uri())

    def _on_echarts_error(self, error_msg: str):
        """ECharts生成失败的回调"""
        self.echarts_btn.config(state=tk.NORMAL)
        self.echarts_status_var.set(f"✗ 生成失败：{error_msg}")
        self.echarts_status_label.config(fg="red")

    def _select_file_for_visualization(self):
        """选择可视化数据源文件，并自动加载年份列表"""
        path = filedialog.askopenfilename(
            filetypes=[("CSV 文件", "*.csv"), ("Excel 文件", "*.xlsx *.xls")]
        )
        if path:
            self.file_path_var_vis.set(f"当前文件: {path}")
            try:
                years = get_available_years(path)
                year_options = ["全部年份（跨年对比）"] + [str(y) for y in years]
                self.year_combo['values'] = year_options
                if len(years) > 1:
                    self.year_combo.current(0)
                else:
                    self.year_combo.current(1 if years else 0)
            except Exception as e:
                messagebox.showerror("错误", f"读取年份失败: {str(e)}")

    def _generate_visualization(self):
        """根据用户选择的图表类型和年份生成HTML并打开"""
        chart_label = self.chart_type_combo.get()
        chart_type = CHART_TYPES.get(chart_label, "heatmap")

        file_path = self.file_path_var_vis.get().split(': ')[-1]
        year_selection = self.year_combo.get()

        self.vis_btn.config(state=tk.DISABLED)
        self.vis_status_var.set(f"正在生成「{chart_label}」，请稍候...")
        self.vis_status_label.config(fg="blue")

        def task():
            try:
                if not file_path:
                    raise ValueError("未选择文件")

                if not year_selection or year_selection.startswith("全部"):
                    year_param = 'all'
                else:
                    year_param = int(year_selection)

                output_dir = self.current_dir
                html_path = generate_chart_html(file_path, output_dir, chart_type,
                                                year=year_param)

                self.root.after(0, lambda: self._on_visualization_done(html_path, chart_label))
            except Exception as e:
                self.root.after(0, lambda e=e: self._on_visualization_error(str(e)))

        threading.Thread(target=task, daemon=True).start()

    def _on_visualization_done(self, html_path: str, chart_label: str):
        """可视化生成完成后的回调（主线程执行）

        Args:
            html_path: 生成的HTML文件路径
            chart_label: 图表类型中文名称
        """
        self.vis_btn.config(state=tk.NORMAL)
        self.vis_status_var.set(f"✓ 「{chart_label}」已保存至：{html_path}")
        self.vis_status_label.config(fg="green")
        webbrowser.open(Path(html_path).as_uri())

    def _on_visualization_error(self, error_msg: str):
        """可视化生成失败的回调（主线程执行）

        Args:
            error_msg: 错误信息
        """
        self.vis_btn.config(state=tk.NORMAL)
        self.vis_status_var.set(f"✗ 生成失败：{error_msg}")
        self.vis_status_label.config(fg="red")

    def create_menu(self):
        """创建菜单栏（文件菜单 + 字体菜单）"""
        menu_bar = tk.Menu(self.root)

        # 文件菜单
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="退出", command=self.root.quit)
        menu_bar.add_cascade(label="文件", menu=file_menu)

        # 字体菜单（含字号子菜单）
        self.font_var = tk.StringVar(value=self.default_font_name)
        font_menu = tk.Menu(menu_bar, tearoff=0)
        for font_name in self.available_fonts:
            font_menu.add_radiobutton(
                label=font_name,
                variable=self.font_var,
                command=lambda n=font_name: self._apply_font(n),
            )

        # 字号子菜单
        size_menu = tk.Menu(font_menu, tearoff=0)
        for size in [10, 11, 12, 13, 14, 15, 16]:
            size_menu.add_radiobutton(
                label=str(size), variable=self.size_var, command=self._apply_font_size
            )
        font_menu.add_cascade(label="字号", menu=size_menu)
        menu_bar.add_cascade(label="字体", menu=font_menu)

        # 关于子菜单
        about_menu = tk.Menu(font_menu, tearoff=0)
        about_menu.add_command(label="关于本软件", command=self._show_about)
        about_menu.add_command(label="使用说明", command=self._show_help)
        about_menu.add_command(label="本项目的开源许可", command=self._show_license)
        about_menu.add_separator()
        about_menu.add_command(label="项目里使用到的其他项目", command=self._show_other_projects)
        menu_bar.add_cascade(label="关于", menu=about_menu)

        self.root.config(menu=menu_bar)

    # ======================== 事件处理 ========================

    def _show_about(self):
        """显示关于对话框"""
        win = tk.Toplevel(self.root)
        win.title("关于")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        win_width, win_height = 360, 320
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        x = (screen_w - win_width) // 2
        y = (screen_h - win_height) // 2
        win.geometry(f"{win_width}x{win_height}+{x}+{y}")

        frame = ttk.Frame(win, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="账单分析工具 v1.1.1", font=("", 14, "bold")).pack(pady=(0, 10))
        ttk.Label(frame, text="一款支持微信支付、支付宝等账单的\n数据分析与可视化工具。", justify=tk.CENTER).pack(
            pady=(0, 10))
        ttk.Label(frame, text="功能包括：\n• 账单数据解析与汇总\n• 词云生成\n• 消费趋势可视化\n• 日历热力图",
                  justify=tk.LEFT).pack(pady=(0, 10))

        link_label = ttk.Label(
            frame,
            text="项目地址：GitHub",
            foreground="blue",
            cursor="hand2",
        )
        link_label.pack(pady=(0, 5))
        link_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/ee19971/Bill_Analyzer"))

        ttk.Button(frame, text="关闭", command=win.destroy).pack(pady=(10, 0))

    def _show_help(self):
        """打开使用说明"""
        help_path = os.path.join(os.path.dirname(__file__), "项目使用说明书.html")
        if os.path.exists(help_path):
            webbrowser.open(f"file://{os.path.abspath(help_path)}")
        else:
            messagebox.showwarning("提示", "未找到使用说明文件")

    def _show_license(self):
        """显示开源许可"""
        webbrowser.open("https://creativecommons.org/licenses/by/4.0/deed.zh-hans")

    def _show_other_projects(self):
        """显示项目里使用到的其他项目"""
        win = tk.Toplevel(self.root)
        win.title("使用过的项目")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        win_width, win_height = 360, 320
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        x = (screen_w - win_width) // 2
        y = (screen_h - win_height) // 2
        win.geometry(f"{win_width}x{win_height}+{x}+{y}")
        frame = ttk.Frame(win, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="图标", font=("", 12, "bold")).pack(pady=(0, 10))
        link_label = ttk.Label(
            frame,
            text="REMIX ICON",
            foreground="blue",
            cursor="hand2",
        )
        link_label.pack(pady=(0, 5))
        link_label.bind("<Button-1>", lambda e: webbrowser.open("https://remixicon.com/"))

        ttk.Label(frame, text="字体", font=("", 12, "bold")).pack(pady=(0, 10))
        link_label = ttk.Label(
            frame,
            text="霞鹜臻楷",
            foreground="blue",
            cursor="hand2",
            font=("", 10, "bold")
        )
        link_label.pack(pady=(0, 5))
        link_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/lxgw/LxgwZhenKai"))
        link_label = ttk.Label(
            frame,
            text="霞鹜新晰黑",
            foreground="blue",
            cursor="hand2",
            font=("", 10, "bold")
        )
        link_label.pack(pady=(0, 5))
        link_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/lxgw/LxgwNeoXiHei"))
        link_label = ttk.Label(
            frame,
            text="得意黑",
            foreground="blue",
            cursor="hand2",
            font=("", 10, "bold")
        )
        link_label.pack(pady=(0, 5))
        link_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/atelier-anchor/smiley-sans"))

    def _select_main_file(self):
        """选择账单文件（支持 CSV 和 Excel）"""
        path = filedialog.askopenfilename(
            filetypes=[("CSV 文件", "*.csv"), ("Excel 文件", "*.xlsx *.xls")]
        )
        if path:
            self.file_path_var_main.set(f"当前文件: {path}")

    def _select_file_for_word_cloud(self):
        """选择词云数据源文件，并自动加载列名"""
        path = filedialog.askopenfilename(
            filetypes=[("CSV 文件", "*.csv"), ("Excel 文件", "*.xlsx *.xls")]
        )
        if not path:
            return

        self.file_path_var_wc.set(f"当前文件: {path}")
        try:
            if path.endswith('.csv'):
                encoding = _detect_encoding(path)
                df = _read_data_file(path, encoding)
            else:
                from cheng_xu.gong_yong_han_shu import find_csv_header_offset
                skip_rows = find_csv_header_offset(path, 'utf-8')
                df = pd.read_excel(path, skiprows=skip_rows)
            columns = list(df.columns)
            self.column_combo['values'] = columns
            self.column_combo.current(0)
        except Exception as e:
            messagebox.showerror("错误", f"文件读取失败: {str(e)}")

    def _select_mask_image(self):
        """选择词云掩码图像文件"""
        path = filedialog.askopenfilename(
            filetypes=[("图片文件", "*.png *.jpg *.jpeg")]
        )
        if path:
            self.mask_image_path.set(path)

    def _get_colormaps(self):
        """获取所有可用的 matplotlib 颜色映射名称"""
        return sorted(plt.colormaps())

    def _apply_font_size(self):
        """应用当前选择的字号"""
        self._apply_font(self.font_var.get())

    def _apply_font(self, font_name):
        """应用选中的字体和字号到UI组件

        Args:
            font_name: 字体名称（不含扩展名）
        """
        self.font_var.set(font_name)
        size = int(self.size_var.get())
        font_path = self._get_font_path(font_name)

        # 获取字体的真实名称
        actual_font_name = font_name
        if font_path:
            try:
                from PIL import ImageFont
                pil_font = ImageFont.truetype(font_path, 12)
                actual_font_name = pil_font.getname()[0]

                # 加载字体到系统
                abs_path = os.path.abspath(font_path)
                ctypes.windll.gdi32.AddFontResourceW(abs_path)
            except Exception as e:
                logger.warning("加载字体失败: %s", e)

        # 只更新字体，不改变其他配置
        if hasattr(self, 'output_text'):
            font_config = self.output_text.cget('font')
            try:
                self.output_text.config(font=(actual_font_name, size))
            except Exception:
                self.output_text.config(font=(font_name, size))

        # 更新matplotlib字体设置
        if font_path:
            self._setup_matplotlib_font(os.path.basename(font_path))

    def _process_file(self):
        """处理账单文件（使用多线程避免 UI 阻塞）

        流程：
        1. 获取文件路径和账单类型
        2. 在子线程中调用对应处理器
        3. 将结果渲染到文本框
        """
        file_path = self.file_path_var_main.get().split(': ')[-1]
        bill_type = self.bill_type.get()

        self.bill_status_var.set(f"正在分析「{bill_type}」账单，请稍候...")
        self.bill_status_label.config(fg="blue")

        def task():
            try:
                if not file_path:
                    raise ValueError("未选择文件")

                processor = BILL_PROCESSORS.get(bill_type)
                if processor is None:
                    raise ValueError(f"不支持的账单类型：{bill_type}")

                result = processor(file_path)
                if result is None:
                    raise ValueError("处理结果为空，请检查文件格式")

                self.current_text = str(result)[:5000]
                self._source_file_path = file_path
                self._source_bill_type = bill_type
                self.root.after(0, lambda: self._show_analysis_result(self.current_text, bill_type))
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda err=error_msg: (
                    self.bill_status_var.set(f"✗ 分析失败：{err}"),
                    self.bill_status_label.config(fg="red"),
                    self._show_analysis_text(f"分析失败：{err}"),
                ))

        threading.Thread(target=task, daemon=True).start()

    def _show_analysis_result(self, text: str, bill_type: str):
        """在文本框中显示分析结果"""
        self.bill_status_var.set(f"✓ 「{bill_type}」账单分析完成")
        self.bill_status_label.config(fg="green")
        self._show_analysis_text(text)

    def _show_analysis_text(self, text: str):
        """在文本框中显示文本内容"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.insert(tk.END, text)
        self.output_text.config(state=tk.DISABLED)

    def _generate_word_cloud(self):
        """生成词云主逻辑

        流程：
        1. 验证输入参数（文件、列名、颜色映射）
        2. 加载字体文件
        3. 调用词云生成函数
        4. 使用 matplotlib 显示结果
        """
        file_path = self.file_path_var_wc.get().split(': ')[-1]
        column_name = self.column_combo.get()
        colormap = self.colormap_combo.get()

        if not all([file_path, column_name, colormap]):
            messagebox.showwarning("警告", "请确保已选择文件、列名和颜色映射")
            return

        try:
            self.wc_status_var.set("正在生成词云，请稍候...")
            self.wc_status_label.config(fg="blue")

            # 获取字体路径
            font_name = self.font_var.get()
            font_path = self._get_font_path(font_name)
            if not font_path:
                raise ValueError(f"未找到字体文件：{font_name}")

            # 调用词云生成函数
            self.current_wordcloud_image = ci_yun(
                file_path,
                column_name,
                file_name=self.mask_image_path.get() or None,
                colormap=colormap,
                font_path=font_path,
            )

            self.wc_status_var.set("✓ 词云生成成功！")
            self.wc_status_label.config(fg="green")

            # 使用 matplotlib 显示图片
            plt.figure(figsize=(10, 8))
            plt.imshow(self.current_wordcloud_image)
            plt.axis("off")
            plt.title("生成的词云图", fontsize=16)
            plt.show()

        except Exception as e:
            error_msg = str(e)
            self.wc_status_var.set(f"✗ 词云生成失败：{error_msg}")
            self.wc_status_label.config(fg="red")
            messagebox.showerror("错误", f"词云生成失败：{error_msg}")

    def _save_word_cloud_image(self):
        """保存词云图片到本地

        文件命名规则：[原文件名]_[列名]_[色表]_[时间戳].png
        """
        if not self.current_wordcloud_image:
            messagebox.showwarning("警告", "请先生成词云")
            return

        file_path = self.file_path_var_wc.get().split(': ')[-1]
        column_name = self.column_combo.get()
        colormap = self.colormap_combo.get()

        if not all([file_path, column_name, colormap]):
            messagebox.showwarning("警告", "请确保已选择文件、列名和颜色映射")
            return

        try:
            # 动态生成文件名
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_col = self._get_safe_filename(column_name)
            safe_cmap = self._get_safe_filename(colormap)
            file_name = f"{base_name}_{safe_col}_{safe_cmap}_{timestamp}.png"

            # 弹出保存对话框
            save_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                initialfile=file_name,
                filetypes=[("PNG 文件", "*.png"), ("所有文件", "*.*")],
            )
            if save_path:
                self.current_wordcloud_image.save(save_path)
                self.wc_status_var.set(f"✓ 词云图片已保存：{save_path}")
                self.wc_status_label.config(fg="green")
            else:
                self.wc_status_var.set("保存操作已取消")
                self.wc_status_label.config(fg="gray")

        except Exception as e:
            error_msg = str(e)
            self.wc_status_var.set(f"✗ 保存失败：{error_msg}")
            self.wc_status_label.config(fg="red")
            messagebox.showerror("错误", f"保存词云图片失败：{error_msg}")


if __name__ == "__main__":
    root = tk.Tk()
    app = BillAnalyzerUI(root)
    root.mainloop()

# Section 尾注 开源许可证

# Bill_Analyzer © 2025 by ee19971 is licensed under Creative Commons Attribution 4.0 International
# https://creativecommons.org/licenses/by/4.0/
