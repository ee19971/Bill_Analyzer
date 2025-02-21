#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------

# @文件：zfb_app.py
# @时间：2025年02月16日09:43
# @作者：ee19971
# @邮箱：3504275453@qq.com
# @作用：统计支付宝导出的账单信息

# ------------------------------------------------------------------------------
# Section 导入模块
import pandas as pd
from gong_yong_han_shu import get_time_period, nan, get_mode_info, search_file_line

# Section 常量
filename = r'C:\test\Bill_Analyzer\alipay.csv'

# 常量
spike = search_file_line(filename, '交易时间,')[0]['line'] - 1
ji_lu = search_file_line(filename, '笔记录')[0]['content']
shou_ru = search_file_line(filename, '收入：')[0]['content']
zhi_chu = search_file_line(filename, '支出：')[0]['content']
bu_ji_shou_zhi = search_file_line(filename, '不计收支：')[0]['content']

zfb_app = pd.read_csv(filename, skiprows=spike, encoding='GB18030')
zfb_app.drop(columns='Unnamed: 12',inplace=True)
# 将日期列转换为date格式
zfb_app["交易时间"] = pd.to_datetime(zfb_app["交易时间"], errors="coerce")
zfb_app = zfb_app.dropna(subset=["交易时间"])
# 将Pandas DataFrame中的列转换为NumPy数组，不然金额可能会算错
expenses = zfb_app["金额"].to_numpy()

# 按'交易时间日'升序排列
zfb_app["交易时间日"] = zfb_app["交易时间"].dt.strftime("%H:%M:%S")
zfb_app = zfb_app.sort_values(by="交易时间日")
print(zfb_app.head())


# print("在{时间}里你花了-2.72元，平均每月花费-0.23元\
#         {1}月花的最多花了-1.37元 {}月花的最少花了-0.03元\
#         收入{2.72}元，平均每月收入{0.23}元\
#         {1}月的收入最多收入了{1.37}元 {1}月的收入最少是{0.01}元\
#         最早的一笔交易是在{25-01-06}的{凌晨}{00:55:52}你{支出}了{-0.03}元\
#         最晚的一笔交易是在{25-01-18}的{晚上}{20:42:17}你收入了{0.03}元\
#         花费最多是在{2025-01-23 01:00:03}因为{ 其它,支付宝转入到余利宝}花了{-1.37}元\
#         最高的收入是在{2025-01-22 17:39:16}因为{ 其它,来自支付宝五福的红包}收入了{1.37}元\
#         {收入0.03 出现了 8 次}")


# Section 尾注 开源许可证

# Bill_Analyzer © 2025 by ee19971 is licensed under Creative Commons Attribution 4.0 International
# https://creativecommons.org/licenses/by/4.0/
