#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------

# @文件：ci_yun.py
# @时间：2025年03月11日15:41
# @作者：ee19971
# @邮箱：3504275453@qq.com
# @作用：Bill_Analyzer项目 - 生成账单选定列的词云图

# ------------------------------------------------------------------------------
"""
词云生成模块

根据账单文件中指定列的文本数据生成词云图片，
支持自定义掩码图和颜色映射。
"""
import os
import random
import logging
import numpy as np
import matplotlib.colors as mcolors
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from chardet import detect
from PIL import Image

from .gong_yong_han_shu import search_file_line, find_csv_header_offset

logger = logging.getLogger(__name__)


def get_safe_filename(name: str) -> str:
    """替换非法字符以生成合法文件名

    Args:
        name: 原始文件名

    Returns:
        str: 替换空格和斜杠后的安全文件名
    """
    return name.replace(" ", "_").replace("/", "_")


def validate_file_path(file_path: str, valid_extensions: tuple) -> None:
    """验证文件路径是否有效

    Args:
        file_path: 文件路径
        valid_extensions: 允许的文件扩展名元组

    Raises:
        ValueError: 文件格式不支持
    """
    if not file_path.lower().endswith(valid_extensions):
        raise ValueError(f"仅支持以下格式：{', '.join(valid_extensions)}")


def _detect_encoding(file_path: str) -> str:
    """自动检测文件编码

    优先使用 chardet 检测，若检测为中文常见编码（GB2312/GBK）或不可靠的
    utf-8/ascii 结果，则统一使用 GB18030（账单文件绝大多数为 GB18030 编码）。

    Args:
        file_path: 文件路径

    Returns:
        str: 检测到的文件编码
    """
    chinese_encodings = {'GB2312', 'GB18030', 'GBK'}
    unreliable_encodings = {'utf-8', 'UTF-8', 'ascii', 'ASCII'}

    with open(file_path, 'rb') as f:
        raw_data = f.read(10000)
        result = detect(raw_data)
        detected = result.get('encoding')
        confidence = result.get('confidence', 0)

    if not detected or detected in chinese_encodings:
        return 'GB18030'

    if detected in unreliable_encodings and confidence < 0.9:
        return 'GB18030'

    return detected

def _read_data_file(file_path: str, encoding: str) -> pd.DataFrame:
    """根据文件扩展名读取数据

    自动检测并跳过账单文件头部的摘要/元数据行。
    若指定编码读取失败，自动回退到 GB18030 和 UTF-8 重试。

    Args:
        file_path: 文件路径
        encoding: 文件编码

    Returns:
        pd.DataFrame: 读取的数据

    Raises:
        ValueError: 文件格式不支持或读取失败
    """
    try:
        if file_path.endswith('.csv'):
            skip_rows = find_csv_header_offset(file_path, encoding)
            try:
                return pd.read_csv(file_path, encoding=encoding, skiprows=skip_rows)
            except (UnicodeDecodeError, UnicodeError, pd.errors.ParserError):
                for fallback_enc in ['GB18030', 'utf-8']:
                    if fallback_enc == encoding:
                        continue
                    try:
                        logger.info("编码 %s 读取失败，尝试回退到 %s", encoding, fallback_enc)
                        skip_rows = find_csv_header_offset(file_path, fallback_enc)
                        return pd.read_csv(file_path, encoding=fallback_enc, skiprows=skip_rows)
                    except Exception:
                        continue
                raise ValueError(f"使用 {encoding} 及回退编码均无法读取文件")
        elif file_path.endswith(('.xlsx', '.xls')):
            skip_rows = find_csv_header_offset(file_path, 'utf-8')
            return pd.read_excel(file_path, skiprows=skip_rows)
        else:
            raise ValueError("不支持的文件格式")
    except ValueError:
        raise
    except (UnicodeDecodeError, pd.errors.ParserError, KeyError) as e:
        raise ValueError(f"读取文件失败: {str(e)}")


class WordCloudGenerator:
    """词云生成器类，封装词云图片的生成逻辑"""

    def __init__(self, font_path: str):
        """初始化词云生成器

        Args:
            font_path: 字体文件路径
        """
        self.font_path = font_path

    def generate(self, text_data: str, mask_image=None, colormap: str = "viridis") -> Image.Image:
        """生成词云图片

        Args:
            text_data: 用于生成词云的文本数据
            mask_image: 掩码图像数组（可选），控制词云形状
            colormap: matplotlib 颜色映射名称

        Returns:
            PIL.Image: 生成的词云图片

        Raises:
            RuntimeError: 词云生成失败
        """
        try:
            cmap = plt.get_cmap(colormap)
            # 使用颜色映射生成随机颜色函数
            color_func = lambda *args, **kwargs: mcolors.rgb2hex(
                cmap(random.random())[:3]
            )

            wordcloud = WordCloud(
                include_numbers=True,
                font_path=self.font_path,
                mask=mask_image,
                width=1800,
                height=1600,
                background_color="black",
                max_words=2000,
                max_font_size=200,
                color_func=color_func,
            ).generate(text_data)

            return wordcloud.to_image()

        except Exception as e:
            raise RuntimeError(f"生成词云失败：{str(e)}")


def ci_yun(file_path: str, list_name: str = None, file_name: str = None,
           colormap: str = 'viridis',
           font_path=r".\f_ont\LXGWNeoXiHeiPlus.ttf") -> Image.Image:
    """生成词云图的主入口函数

    Args:
        file_path: 输入文件路径（支持CSV和Excel）
        list_name: 要分析的列名
        file_name: 掩码图像路径（可选）
        colormap: 颜色映射名称（可选，默认为 'viridis'）
        font_path: 自定义字体路径

    Returns:
        PIL.Image: 生成的词云图片

    Raises:
        ValueError: 文件格式不支持或列名不存在
        FileNotFoundError: 字体文件或掩码文件不存在
    """
    # 验证文件格式
    validate_file_path(file_path, ('.csv', '.xlsx', '.xls'))

    # 检测文件编码并读取数据
    encoding = _detect_encoding(file_path)
    logger.debug("文件编码: %s", encoding)

    df = _read_data_file(file_path, encoding)

    # 验证列名
    if list_name not in df.columns:
        raise KeyError(f"列名 '{list_name}' 不存在于文件中，请检查列名是否正确。")

    # 数据预处理：合并非空文本并替换特殊字符
    text_series = df[list_name].dropna().astype(str)
    text_series = text_series[text_series.str.strip() != ""]
    text_data = " ".join(text_series)
    # text_data = text_data.replace('*', '_').replace('.', '_')

    # 加载掩码图像（可选）
    mask_array = None
    if file_name:
        try:
            if not os.path.exists(file_name):
                raise FileNotFoundError(f"掩码图像不存在: {file_name}")
            mask_array = np.array(Image.open(file_name))
            logger.debug("成功加载掩码图像: %s", file_name)
        except Exception as e:
            logger.warning("加载掩码图像失败: %s", e)

    # 验证字体并生成词云
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"字体文件不存在：{font_path}")

    generator = WordCloudGenerator(font_path)
    return generator.generate(text_data, mask_array, colormap)


# Section 尾注 开源许可证

# Bill_Analyzer © 2025 by ee19971 is licensed under Creative Commons Attribution 4.0 International
# https://creativecommons.org/licenses/by/4.0/
