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
from gong_yong_han_shu import get_time_period, nan, get_mode_info


# Section 获取当前工作目录
current_directory = os.getcwd()
# !!!自己填csv名字
file_path = os.path.join(current_directory, "zfb2.csv")

# Section 导入账单
zfb = pd.read_csv(file_path, encoding="gb18030", skiprows=4)
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

# Section 计算最大支出和最小支出
max_expense = zfb["支出金额（-元）"].min()  # 最大支出
max_expense_row = zfb.loc[zfb["支出金额（-元）"] == max_expense].iloc[
    0
]  # 最大支出行索引
max_expense_name = max_expense_row["商品名称"].strip()  # 最大支出商品
max_expense_type = max_expense_row["业务类型"].strip()  # 最大支出类型
max_expense_remark = max_expense_row["备注"].strip()  # 最大支出备注
max_expense_reason = (
    max_expense_name
    + ("," if max_expense_name != "" else " ")
    + max_expense_type
    + ","
    + max_expense_remark
)  # 最大支出原因

# sorted_expense = zfb['支出金额（-元）'].sort_values(ascending=False)  # 计算最小支出
# min_expense = None
# for expense in sorted_expense:
#     if expense < 0.00:
#         min_expense = expense
#         break
# if min_expense is None:
#     min_expense = 0.00  这是我自己写的下面是通义写的🤣

# 计算最小支出金额（即绝对值最小的负数）
min_expense = (
    zfb[zfb["支出金额（-元）"] < 0]["支出金额（-元）"].max() or 0.00
)  # 最小支出

# Section 计算最大收入和最小收入
# sorted_income = zfb['收入金额（+元）'].sort_values()  # 计算最小收入
# min_income = None
# for income in sorted_income:
#     if income > 0.00:
#         min_income = income
#         break
# if min_income is None:
#     min_income = 0.00
min_income = (
    zfb[zfb["收入金额（+元）"] > 0]["收入金额（+元）"].min() or 0.00
)  # 最小收入

max_income = zfb["收入金额（+元）"].max()  # 最大收入
max_income_row = zfb.loc[zfb["收入金额（+元）"] == max_income].iloc[0]
max_income_name = max_income_row["商品名称"].strip()  # 最大收入商品
max_income_type = max_income_row["业务类型"].strip()  # 最大收入类型
max_income_remark = max_income_row["备注"].strip()  # 最大收入备注
max_income_reason = (
    max_income_name
    + ("," if max_income_name != "" else " ")
    + max_income_type
    + ","
    + max_income_remark
)  # 最大收入原因

# Section 计算年收入和年支出
total_income_year = incomes.sum()  # 计算年收入
average_income_month = total_income_year / 12  # 计算月平均收入
total_expense_year = expenses.sum()  # 计算年支出
average_expense_month = total_expense_year / 12  # 计算月平均支

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
transaction_type_1 = (
    "支出" if earliest < 0 else "收入"
)  # 判断最早的一笔交易内容是支出还是收入

# 最晚
latest_row = zfb.iloc[-1]
latest_transaction_date = latest_row["发生时间"]  # 最晚的一笔交易时间
shi_jian_2 = get_time_period(latest_transaction_date.hour)

latest = (
    latest_row["支出金额（-元）"]
    if latest_row["收入金额（+元）"] == 0.00
    else latest_row["收入金额（+元）"]
)  # 最晚的一笔交易内容
transaction_type_2 = (
    "支出" if latest < 0 else "收入"
)  # 判断最晚的一笔交易内容是支出还是收入
# 提取最小支出和最小收入的月份
min_expense_month = zfb.loc[
    zfb["支出金额（-元）"] == min_expense, "发生时间"
].dt.month.iloc[
    0
]  # 最小支出的月份
max_expense_month = zfb.loc[
    zfb["支出金额（-元）"] == max_expense, "发生时间"
].dt.month.iloc[
    0
]  # 最大支出的月份
min_income_month = zfb.loc[
    zfb["收入金额（+元）"] == min_income, "发生时间"
].dt.month.iloc[
    0
]  # 最小收入的月份
max_income_month = zfb.loc[
    zfb["收入金额（+元）"] == max_income, "发生时间"
].dt.month.iloc[
    0
]  # 最大收入的月份
# 提取最大支出和最大收入的时间
max_expense_time = zfb.loc[zfb["支出金额（-元）"] == max_expense, "发生时间"].iloc[
    0
]  # 最大支出的时间
max_income_time = zfb.loc[zfb["收入金额（+元）"] == max_income, "发生时间"].iloc[
    0
]  # 最大收入的时间
# Section 查看众数
# 使用 get_mode_info 函数获取众数信息
mode_number = get_mode_info(zfb["支出金额（-元）"], zfb["收入金额（+元）"])

# Section 总结
print(
    f"在{year}年你花了{total_expense_year}元，平均每月花费{average_expense_month:.2f}元\r\n"
    f"{max_expense_month}月花的最多花了{max_expense}元 {min_expense_month}月花的最少花了{min_expense}元\r\n"
    f"收入{total_income_year}元，平均每月收入{average_income_month:.2f}元\r\n"
    f"{max_income_month}月的收入最多收入了{max_income}元 {min_income_month}月的收入最少是{min_income}元\r\n"
    f"最早的一笔交易是在{earliest_transaction_date.strftime("%y-%m-%d")}的{shi_jian_1}"
    f"{earliest_transaction_date.strftime("%H:%M:%S")}你{transaction_type_1}了{earliest}元\r\n"
    f"最晚的一笔交易是在{latest_transaction_date.strftime("%y-%m-%d")}的{shi_jian_2}"
    f"{latest_transaction_date.strftime("%H:%M:%S")}你{transaction_type_2}了{latest}元\r\n"
    f"花费最多是在{max_expense_time}因为{max_expense_reason}花了{max_expense}元\r\n"
    f"最高的收入是在{max_income_time}因为{max_income_reason}收入了{max_income}元\r\n"
    f"{mode_number}"
)

# Section 尾注 开源许可证

# Bill_Analyzer © 2025 by ee19971 is licensed under Creative Commons Attribution 4.0 International
# https://creativecommons.org/licenses/by/4.0/