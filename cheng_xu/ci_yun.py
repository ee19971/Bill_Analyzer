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

def ci_yun(file_path: str, list_name: str = None, file_name: str = None, colormap: str = 'viridis'):
    """
    生成词云图
    :param file_path: 输入文件路径（支持CSV和Excel）
    :param list_name: 要分析的列名
    :param file_name: 掩码图像路径（可选）
    :param colormap: 颜色映射名称（可选，默认为 'viridis'）
    """
    # 检查文件扩展名
    valid_extensions = ('.csv', '.xlsx', '.xls')
    if not file_path.lower().endswith(valid_extensions):
        raise ValueError("仅支持CSV和Excel文件")

    # section 检测文件编码
    encoding_map = ['GB2312', 'GB18030', 'GBK']  # 常见错误编码映射
    with open(file_path, 'rb') as f:
        encoding = detect(f.read(10000))['encoding']
    print(f"文件编码为：{encoding}")
    if encoding in encoding_map:
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
    try:
        font_path = r".\f_ont\LXGWNeoXiHeiPlus.ttf"
        if not os.path.exists(font_path):
            raise FileNotFoundError(f"字体文件不存在：{font_path}")

        # 获取颜色映射
        cmap = plt.get_cmap(colormap)
        color_func = lambda *args, **kwargs: mcolors.rgb2hex(cmap(random.random())[:3])

        wordcloud = WordCloud(
            include_numbers=True,
            font_path=font_path,  # 中文字体路径
            mask=mask_array,
            width=1800,  # 图片宽度
            height=1600,  # 图片高度
            background_color="white",  # 背景色
            max_words=2000,  # 最大词数
            max_font_size=200,  # 字体最大值
            color_func=color_func  # 颜色函数
        ).generate(text_data)  # 生成词云

        # 保存词云图片
        output_path = r"..\词云图.png"
        wordcloud.to_file(output_path)
        print(f"词云图片已保存到：{output_path}")

    except Exception as e:
        raise RuntimeError(f"生成词云失败：{str(e)}")

    # section 显示图片
    plt.figure(figsize=(18, 16))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")  # 隐藏坐标轴
    plt.show()
