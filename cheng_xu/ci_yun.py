#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------

# @文件：ci_yun.py
# @时间：2025年03月11日15:41
# @作者：ee19971
# @邮箱：3504275453@qq.com
# @作用：Bill_Analyzer项目${生成账单选定列的词云图}

# ------------------------------------------------------------------------------
# section 导入包
import os
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from chardet import detect
from PIL import Image, UnidentifiedImageError
import numpy as np
import matplotlib.colors as mcolors
import random


def get_safe_filename(name):
    """替换非法字符以生成合法文件名"""
    return name.replace(" ", "_").replace("/", "_")


def validate_file_path(file_path, valid_extensions):
    """验证文件路径是否有效"""
    if not file_path.lower().endswith(valid_extensions):
        raise ValueError(f"仅支持以下格式：{', '.join(valid_extensions)}")


class WordCloudGenerator:
    def __init__(self, font_path):
        self.font_path = font_path

    def generate(self, text_data, mask_image=None, colormap="viridis"):
        """生成词云图片"""
        try:
            cmap = plt.get_cmap(colormap)
            color_func = lambda *args, **kwargs: mcolors.rgb2hex(cmap(random.random())[:3])

            wordcloud = WordCloud(
                include_numbers=True,
                font_path=self.font_path,
                mask=mask_image,
                width=1800,
                height=1600,
                background_color="black",
                max_words=2000,
                max_font_size=200,
                color_func=color_func
            ).generate(text_data)

            return wordcloud.to_image()

        except Exception as e:
            raise RuntimeError(f"生成词云失败：{str(e)}")


def ci_yun(file_path: str, list_name: str = None, file_name: str = None, colormap: str = 'viridis',
           font_path=r".\f_ont\LXGWNeoXiHeiPlus.ttf"):
    """
    生成词云图
    :param font_path: 自定义字体路径
    :param file_path: 输入文件路径（支持CSV和Excel）
    :param list_name: 要分析的列名
    :param file_name: 掩码图像路径（可选）
    :param colormap: 颜色映射名称（可选，默认为 'viridis'）
    :return: 生成的词云图片
    """
    # 检查文件扩展名
    valid_extensions = ('.csv', '.xlsx', '.xls')
    validate_file_path(file_path, valid_extensions)

    # section 检测文件编码
    encoding_map = ['GB2312', 'GB18030', 'GBK']  # 常见错误编码映射
    with open(file_path, 'rb') as f:
        encoding = detect(f.read(10000))['encoding']
    print(f"文件编码为：{encoding}")
    # 如果检测失败，默认使用 GB18030 编码
    if not encoding or encoding in encoding_map:
        encoding = 'GB18030'
    print(f"文件编码修正为：{encoding}")

    # section 读取文件
    try:
        if file_path.endswith('.csv'):
            # CSV文件处理逻辑
            df = pd.read_csv(file_path, encoding=encoding)
        elif file_path.endswith(('.xlsx', '.xls')):
            # Excel文件直接读取
            df = pd.read_excel(file_path)
        else:
            raise ValueError("不支持的文件格式")

        # 确保列名存在
        if list_name not in df.columns:
            raise KeyError(f"列名 '{list_name}' 不存在于文件中，请检查列名是否正确。")

        # 将列数据转换为字符串类型
        df[list_name] = df[list_name].astype(str)

    except (UnicodeDecodeError, KeyError) as e:
        raise ValueError(f"读取文件失败: {str(e)}")

    # section 数据预处理
    # 合并非空文本
    text_data = " ".join(df[list_name].dropna())
    print(f"提取的文本数据（原始）：\n{text_data[:100]}...")  # 打印前100个字符以供调试

    # 替换 * 和 . 为 _
    text_data = text_data.replace('*', '_').replace('.', '_')
    print(f"提取的文本数据（处理后）：\n{text_data[:100]}...")  # 打印前100个字符以供调试

    # section 加载掩码图像
    mask_array = None
    if file_name and os.path.exists(file_name):
        try:
            mask_image = Image.open(file_name)
            mask_array = np.array(mask_image)
            print(f"成功加载掩码图像：{file_name}")
        except (UnidentifiedImageError, FileNotFoundError) as e:
            print(f"加载掩码图像失败：{str(e)}")

    # section 生成词云
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"字体文件不存在：{font_path}")

    generator = WordCloudGenerator(font_path)
    return generator.generate(text_data, mask_array, colormap)

# Section 尾注 开源许可证

# Bill_Analyzer © 2025 by ee19971 is licensed under Creative Commons Attribution 4.0 International
# https://creativecommons.org/licenses/by/4.0/
