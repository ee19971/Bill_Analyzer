#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------

# @文件：__init__.py
# @时间：2025年02月16日09:30
# @作者：ee19971
# @邮箱：3504275453@qq.com
# @作用：使cheng_xu目录被识别为python包然后使用目录里的文件。

# ------------------------------------------------------------------------------
__version__ = "1.0.0"  # 包版本号
__author__ = "ee19971"
__email__ = "3504275453@qq.com"

from .wx import wx_csv
from .zfb_wy import zfb_wy_csv
from .zfb_app_zhong_wen import zfb_app_zhong_wen_csv
from .ci_yun import ci_yun

# 定义允许导入的内容
__all__ = [
    "wx_csv",
    "zfb_wy_csv",
    "zfb_app_zhong_wen_csv",
    "ci_yun",
]

# Section 尾注 开源许可证

# Bill_Analyzer © 2025 by ee19971 is licensed under Creative Commons Attribution 4.0 International
# https://creativecommons.org/licenses/by/4.0/