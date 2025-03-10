#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ✔️to-do：添加图形化界面并打包
# todo：添加汇率转换
# todo：添加图表可视化
# todo：支出记账软件的账单
# todo：支持银行app导出的账单

# !/usr/bin/env python
# -*- coding: utf-8 -*-

from cheng_xu import wx_csv, zfb_wy_csv, zfb_app_zhong_wen_csv
from PIL import Image, ImageDraw, ImageFont, ImageTk
import sys
import os
from tkinter import messagebox
import tkinter as tk
from tkinter import filedialog, ttk


class BillAnalyzerUI:
    def __init__(self, root):
        self.root = root
        self.root.title("账单分析工具 v1.0")
        self.root.geometry("800x600")

        # 获取当前工作目录（即 .exe 文件所在目录）
        current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))  # 使用 sys.argv[0] 获取 .exe 文件路径

        # 字体相关初始化
        self.font_dir = os.path.join(current_dir, "f_ont")  # 相对路径指向外部的 f_ont 文件夹
        self.default_font = "LXGWNeoXiHeiPlus.ttf"  # 默认字体文件名（含扩展名）
        self.default_font_name = os.path.splitext(self.default_font)[0]  # 去掉扩展名后的默认字体名称
        self.size_var = tk.StringVar(value="15")  # 默认字号

        # 验证默认字体是否存在
        if not self.validate_default_font():
            return

        # 加载可用字体列表
        self.available_fonts = self.load_custom_fonts()

        # 初始化界面组件
        self.create_ui_components()


    def validate_default_font(self):
        """验证默认字体文件是否存在"""
        default_font_path = os.path.join(self.font_dir, self.default_font)
        if not os.path.exists(default_font_path):
            messagebox.showerror(
                "致命错误",
                f"缺失关键字体文件：{self.default_font}\n请检查 {self.font_dir} 目录。",
            )
            self.root.destroy()
            return False
        return True

    def load_custom_fonts(self):
        """加载自定义字体文件并返回字体名称列表"""
        custom_fonts = []
        if not os.path.exists(self.font_dir):
            messagebox.showerror("错误", f"字体目录不存在: {self.font_dir}")
            return [self.default_font_name]

        for f in os.listdir(self.font_dir):
            if f.lower().endswith(('.ttf', '.otf')):
                font_name = os.path.splitext(f)[0]  # 去掉扩展名
                custom_fonts.append(font_name)

        # 确保默认字体在列表首位
        if self.default_font_name not in custom_fonts:
            custom_fonts.insert(0, self.default_font_name)

        return custom_fonts

    def create_ui_components(self):
        """创建界面组件"""
        # 文件路径显示标签
        self.file_var = tk.StringVar()
        tk.Label(self.root, textvariable=self.file_var).pack(pady=10)

        # 文件选择按钮
        tk.Button(self.root, text="选择文件", command=self.select_file).pack(pady=10)

        # 账单类型选择下拉框
        self.bill_type = tk.StringVar(value="微信app导出")
        ttk.Combobox(
            self.root,
            textvariable=self.bill_type,
            values=["微信app导出", "支付宝网页导出", "支付宝APP中文导出"],
        ).pack(pady=10)

        # 运行分析按钮
        tk.Button(self.root, text="运行分析", command=self.process_file).pack(pady=10)

        # 输出画布
        self.output_canvas = tk.Canvas(self.root, height=400, bg="white")
        self.output_canvas.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        self.current_image = None

        # 创建菜单栏
        self.create_menu()

    def create_menu(self):
        """创建菜单栏"""
        menu_bar = tk.Menu(self.root)

        # 文件菜单
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="退出", command=self.root.quit)
        menu_bar.add_cascade(label="文件", menu=file_menu)

        # 字体菜单
        self.font_var = tk.StringVar(value=self.default_font_name)
        font_menu = tk.Menu(menu_bar, tearoff=0)
        for font_name in self.available_fonts:
            font_menu.add_radiobutton(
                label=font_name,
                variable=self.font_var,
                command=lambda n=font_name: self.apply_font(n),
            )
        menu_bar.add_cascade(label="字体", menu=font_menu)

        # 字号子菜单
        size_menu = tk.Menu(font_menu, tearoff=0)
        for size in [10, 11, 12, 13, 14, 15, 16]:
            size_menu.add_radiobutton(
                label=str(size), variable=self.size_var, command=self.apply_font_size
            )
        font_menu.add_cascade(label="字号", menu=size_menu)

        self.root.config(menu=menu_bar)

    def select_file(self):
        """打开文件选择对话框，并更新文件路径显示"""
        path = filedialog.askopenfilename()
        if path:
            self.file_var.set(f"当前文件: {path}")

    def process_file(self):
        """处理账单文件并显示结果"""
        file_path = self.file_var.get().split(': ')[-1]
        if not file_path:
            messagebox.showwarning("警告", "请先选择文件")
            return

        try:
            if self.bill_type.get() == "微信app导出":
                result = wx_csv(file_path)
            elif self.bill_type.get() == "支付宝网页导出":
                result = zfb_wy_csv(file_path)
            elif self.bill_type.get() == "支付宝APP中文导出":
                result = zfb_app_zhong_wen_csv(file_path)
            else:
                raise ValueError("未知账单类型")

            self.current_text = str(result)[:5000]
            self.apply_font(self.font_var.get())

        except Exception as e:
            messagebox.showerror("错误", f"处理失败: {str(e)}")

    def apply_font_size(self):
        """应用当前选择的字号"""
        self.apply_font(self.font_var.get())

    def apply_font(self, font_name):
        """应用字体并渲染文本到画布"""
        try:
            text_content = self.current_text
            font_size = int(self.size_var.get())
            image = Image.new("RGB", (800, 500), "white")
            draw = ImageDraw.Draw(image)

            # 获取字体文件路径
            font_path = self.get_font_path(font_name)
            if not font_path:
                raise FileNotFoundError(f"未找到字体文件: {font_name}")

            # 加载字体
            image_font = ImageFont.truetype(font_path, font_size)

            # 渲染文本
            x, y = 10, 10
            for line in text_content.split('\n'):
                bbox = draw.textbbox((x, y), line, font=image_font)  # 使用 getbbox 方法获取文本边界框
                draw.text((x, y), line, font=image_font, fill="black")
                y += bbox[3] - bbox[1] + 5  # 根据 bbox 计算行高

            # 更新Canvas显示
            self.current_image = ImageTk.PhotoImage(image)
            self.output_canvas.delete("all")
            self.output_canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image)

        except Exception as e:
            error_details = f"""字体加载失败详细诊断：
            1. 字体目录：{self.font_dir}
            2. 尝试加载的字体：{font_name}
            3. 当前工作目录：{os.getcwd()}
            4. 错误类型：{type(e).__name__}
            5. 错误详情：{str(e)}"""
            messagebox.showerror("字体错误", error_details)

    def get_font_path(self, font_name):
        """根据字体名称获取字体文件路径"""
        possible_extensions = ['.ttf', '.otf', '.TTF', '.OTF']
        for ext in possible_extensions:
            test_path = os.path.join(self.font_dir, f"{font_name}{ext}")
            if os.path.exists(test_path):
                return test_path
        return None


if __name__ == "__main__":
    root = tk.Tk()
    app = BillAnalyzerUI(root)
    root.mainloop()

# Section 尾注 开源许可证

# Bill_Analyzer © 2025 by ee19971 is licensed under Creative Commons Attribution 4.0 International
# https://creativecommons.org/licenses/by/4.0/
