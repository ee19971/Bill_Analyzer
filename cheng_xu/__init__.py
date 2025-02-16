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
# 暴露公共接口
from .gong_yong_han_shu import get_time_period, nan, get_mode_info

# 定义允许导入的内容
__all__ = [
    "get_time_period",
    "get_mode_info",
]
