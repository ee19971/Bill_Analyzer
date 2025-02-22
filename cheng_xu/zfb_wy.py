#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------

# @文件：zfb_wy.py
# @时间：2025年02月16日09:43
# @作者：ee19971
# @邮箱：3504275453@qq.com
# @作用：统计支付宝网页版导出的账单信息

# ------------------------------------------------------------------------------
# Section 导入模块
import pandas as pd
import os
from gong_yong_han_shu import (
    get_time_period,
    nan,
    get_mode_info,
    calculate_financial_extremes  # 新增导入
)

# Section 获取当前工作目录
current_directory = os.getcwd()
# !!!自己填csv名字
file_path = os.path.join(current_directory, "zfb2.csv")

# Section 导入账单
zfb = pd.read_csv(r'C:\test\Bill_Analyzer\zfb.csv', encoding="gb18030", skiprows=4)
# Section 数据清洗
# 将日期列转换为date格式
zfb["发生时间"] = pd.to_datetime(zfb["发生时间"], errors="coerce")
zfb = zfb.dropna(subset=["发生时间"])
# 将Pandas DataFrame中的列转换为NumPy数组，不然金额可能会算错
expenses = zfb["支出金额（-元）"].to_numpy()
incomes = zfb["收入金额（+元）"].to_numpy()

# 按'发生时间1'升序排列
zfb["发生时间1"] = zfb["发生时间"].dt.strftime("%H:%M:%S")
zfb = zfb.sort_values(by="发生时间1")

# 定义变量
# 提取时间信息
year = zfb["发生时间"].dt.year.iloc[0]  # 提取年份
month = zfb["发生时间"].dt.month  # 提取月份

extremes = calculate_financial_extremes(zfb, "商品名称", "业务类型", "备注")
max_expense = extremes['max_expense']['amount']
max_expense_reason = extremes['max_expense']['reason']
min_expense = extremes['min_expense']['amount']
max_income = extremes['max_income']['amount']
max_income_reason = extremes['max_income']['reason']
min_income = extremes['min_income']['amount']

# Section 计算年收入和年支出
total_income_month = incomes.sum()  # 计算月收入
average_income_day = total_income_month / 31  # 计算日平均收入
total_expense_month = expenses.sum()  # 计算月支出
average_expense_day = total_expense_month / 31  # 计算日平均支出

# Section 找到最早和最晚的交易
# 最早
earliest_row = zfb.iloc[0]
earliest_transaction_date = earliest_row["发生时间"]  # 最早的一笔交易时间
shi_jian_1 = get_time_period(earliest_transaction_date.hour)

earliest = (
    earliest_row["支出金额（-元）"]
    if earliest_row["收入金额（+元）"] == 0.00
    else earliest_row["收入金额（+元）"]
)  # 最早的一笔交易内容
transaction_type_1 = ("支出" if earliest < 0 else "收入")  # 判断最早的一笔交易内容是支出还是收入

# 最晚
latest_row = zfb.iloc[-1]
latest_transaction_date = latest_row["发生时间"]  # 最晚的一笔交易时间
shi_jian_2 = get_time_period(latest_transaction_date.hour)

latest = (
    latest_row["支出金额（-元）"]
    if latest_row["收入金额（+元）"] == 0.00
    else latest_row["收入金额（+元）"]
)  # 最晚的一笔交易内容
transaction_type_2 = ("支出" if latest < 0 else "收入")  # 判断最晚的一笔交易内容是支出还是收入
# 提取最小支出和最小收入的月份
min_expense_day = zfb.loc[zfb["支出金额（-元）"] == min_expense, "发生时间"].dt.strftime("%m月%d日").iloc[0]   # 最小支出的月份
max_expense_day = zfb.loc[zfb["支出金额（-元）"] == max_expense, "发生时间"].dt.strftime("%m月%d日").iloc[0]  # 最大支出的月份
min_income_day = zfb.loc[zfb["收入金额（+元）"] == min_income, "发生时间"].dt.strftime("%m月%d日").iloc[0]  # 最小收入的月份
max_income_day = zfb.loc[zfb["收入金额（+元）"] == max_income, "发生时间"].dt.strftime("%m月%d日").iloc[0]  # 最大收入的月份
# 提取最大支出和最大收入的时间
max_expense_time = zfb.loc[zfb["支出金额（-元）"] == max_expense, "发生时间"].iloc[0]  # 最大支出的时间
max_income_time = zfb.loc[zfb["收入金额（+元）"] == max_income, "发生时间"].iloc[0]  # 最大收入的时间

# Section 查看众数
# 使用 get_mode_info 函数获取众数信息
mode_number = get_mode_info(zfb["支出金额（-元）"], zfb["收入金额（+元）"])

# Section 总结
print(
    f"在31天里，你总共花费了{total_expense_month}元，平均每天花费{average_expense_day:.2f}元。\r\n"
    f"你总共收入了{total_income_month}元，平均每天收入{average_income_day:.2f}元。\r\n"
    f"{max_expense_day}是你花费最多的一天，花费了{max_expense}元；{min_expense_day}是你花费最少的一天，花费了{min_expense}元。\r\n"
    f"{max_income_day}是你收入最多的一天，收入了{max_income}元；{max_income_day}是你收入最少的一天，收入了{min_income}元。\r\n"
    f"你的总收入为{total_income_month}元，平均每天收入{average_income_day:.2f}元。\r\n"
    f"你的总支出为{total_expense_month}元，平均每天支出{average_expense_day:.2f}元。\r\n"
    f"最早的一笔交易是在{earliest_transaction_date.strftime('%y-%m-%d')}的{shi_jian_1} "
    f"{earliest_transaction_date.strftime('%H:%M:%S')}，你{transaction_type_1}了{earliest}元。\r\n"
    f"最晚的一笔交易是在{latest_transaction_date.strftime('%y-%m-%d')}的{shi_jian_2} "
    f"{latest_transaction_date.strftime('%H:%M:%S')}，你{transaction_type_2}了{latest}元。\r\n"
    f"\r\n"
    f"你花费最多的一笔交易是在{max_expense_time}，因为{max_expense_reason}，花费了{max_expense}元。\r\n"
    f"你收入最多的一笔交易是在{max_income_time}，因为{max_income_reason}，收入了{max_income}元。\r\n"
    f"{mode_number}"
)

print(
    f"【账单统计周期】31天\r\n"
    f"• 总支出：{total_expense_month}元 | 日均支出：{average_expense_day:.2f}元\r\n"
    f"• 总收入：{total_income_month}元 | 日均收入：{average_income_day:.2f}元\r\n\r\n"

    f"【极端收支情况】\r\n"
    f"▷ 单日最高支出：{max_expense_day} ({max_expense}元)\r\n"
    f"▷ 单日最低支出：{min_expense_day} ({min_expense}元)\r\n"
    f"▷ 单日最高收入：{max_income_day} ({max_income}元)\r\n"
    f"▷ 单日最低收入：{min_income_day} ({min_income}元)\r\n\r\n"

    f"【特殊交易记录】\r\n"
    f"最早交易：{earliest_transaction_date.strftime('%Y-%m-%d')} {shi_jian_1} "
    f"{earliest_transaction_date.strftime('%H:%M:%S')} | {transaction_type_1} {earliest}元\r\n"
    f"最晚交易：{latest_transaction_date.strftime('%Y-%m-%d')} {shi_jian_2} "
    f"{latest_transaction_date.strftime('%H:%M:%S')} | {transaction_type_2} {latest}元\r\n\r\n"

    f"【重点交易明细】\r\n"
    f"• 最大支出：{max_expense_time.strftime('%Y-%m-%d %H:%M:%S')}\r\n"
    f"  金额：{max_expense}元 | 事由：{max_expense_reason}\r\n"
    f"• 最高收入：{max_income_time.strftime('%Y-%m-%d %H:%M:%S')}\r\n"
    f"  金额：{max_income}元 | 来源：{max_income_reason}\r\n\r\n"

    f"【交易频次分析】\r\n"
    f"{mode_number}"
)




# Section 尾注 开源许可证

# Bill_Analyzer © 2025 by ee19971 is licensed under Creative Commons Attribution 4.0 International
# https://creativecommons.org/licenses/by/4.0/
