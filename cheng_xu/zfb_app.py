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
from gong_yong_han_shu import get_time_period, nan, get_mode_info, search_file_line, calculate_financial_extremes

# Section 常量
filename = r'C:\test\Bill_Analyzer\alipay.csv'
spike = search_file_line(filename, '交易时间,')[0]['line'] - 1
ji_lu = search_file_line(filename, '笔记录')[0]['content']
shou_ru = search_file_line(filename, '收入：')[0]['content']
zhi_chu = search_file_line(filename, '支出：')[0]['content']
bu_ji_shou_zhi = search_file_line(filename, '不计收支：')[0]['content']

# section 读取文件
zfb_app = pd.read_csv(filename, skiprows=spike, encoding='GB18030')
zfb_app.drop(columns='Unnamed: 12', inplace=True)  # 删掉一个没有用的列
# 将日期列转换为date格式
zfb_app["交易时间"] = pd.to_datetime(zfb_app["交易时间"], errors="coerce")  # 将“交易时间”列转换为日期时间格式，无法解析的值设为NaT
zfb_app.dropna(subset=["交易时间"],inplace=True)  # 删除“交易时间”列中包含NaT的行


# section 把金额列的内容按“收/支”列转到新列，如果是收入把金额转到“收入金额”列，如果是支出转到“支出金额”列
# 创建布尔掩码（mask）标识符合条件的数据行
mask_income = zfb_app["收/支"] == "收入"  # 标记所有"收入"行
mask_expense = zfb_app["收/支"] == "支出"  # 标记所有"支出"行

# 创建收入金额列（向量化操作）
zfb_app["收入金额"] = zfb_app["金额"].where(mask_income, 0.0)
# 解释：对金额列取值，当mask_income为True时保留原值，否则填0.0

# 创建支出金额列（向量化操作）
zfb_app["支出金额"] = (-zfb_app["金额"].abs()).where(mask_expense, 0.0)
# 解释：
# 1. zfb_app["金额"].abs()：取金额绝对值
# 2. 添加负号：确保支出金额为负数
# 3. .where(mask_expense, 0.0)：仅当mask_expense为True时生效，否则填0.0

# 修改原始金额列（向量化操作）
zfb_app.loc[mask_income | mask_expense, "金额"] = 0.0
# 解释：
# mask_income | mask_expense：合并收入/支出的布尔掩码
# 对符合条件的行（收入或支出），将金额列设为0.0
# "不计收支"的行保持原值不变

# 将Pandas DataFrame中的列转换为NumPy数组，不然金额可能会算错
money = zfb_app["金额"].to_numpy()  # 将“金额”列转换为NumPy数组
expense = zfb_app["支出金额"].to_numpy()  # 将“支出金额”列转换为NumPy数组
income = zfb_app["收入金额"].to_numpy()  # 将“收入金额”列转换为NumPy数组

# section 按'交易时间日'升序排列
zfb_app["交易时间日"] = zfb_app["交易时间"].dt.strftime("%H:%M:%S")
zfb_app = zfb_app.sort_values(by="交易时间日")

# 填充空值
text_columns = ['商品说明', '收/付款方式', '备注', '商家订单号']  # 文本列填充空字符串
numeric_columns = ['金额', '收入金额', '支出金额']  # 数值列填充 0.0
zfb_app[text_columns] = zfb_app[text_columns].fillna("")  # 文本列空值替换
zfb_app[numeric_columns] = zfb_app[numeric_columns].fillna(0.0)  # 数值列空值替换

# section 判断极值
extremes = calculate_financial_extremes(
    df=zfb_app,
    name_col="商品说明",
    type_col="交易分类",
    remark_col="备注",
    expense_col="支出金额",
    income_col="收入金额"
)
max_expense = extremes['max_expense']['amount']  # 最大支出金额
max_expense_reason = extremes['max_expense']['reason']  # 最大支出的原因
min_expense = extremes['min_expense']['amount']  # 最小支出金额
max_income = extremes['max_income']['amount']  # 最大收入金额
max_income_reason = extremes['max_income']['reason']  # 最大收入的原因
min_income = extremes['min_income']['amount']  # 最小收入金额

# Section 处理数值
total_duration = (zfb_app["交易时间"].max() - zfb_app["交易时间"].min()).days  # 计算账单总天数
earliest_row = zfb_app.iloc[0]  # 获取最早的一行数据
earliest_transaction_date = earliest_row["交易时间"]  # 获取最早交易的时间
shi_jian_1 = get_time_period(earliest_transaction_date.hour)  # 获取最早交易时间的时段
latest_row = zfb_app.iloc[-1]  # 获取最晚的一行数据
latest_transaction_date = latest_row["交易时间"]  # 获取最晚交易的时间
shi_jian_2 = get_time_period(latest_transaction_date.hour)  # 获取最晚交易时间的时段

total_income_month = income.sum()  # 计算年收入
average_income_day = total_income_month / total_duration  # 计算日平均收入
total_expense_month = expense.sum()  # 计算年支出
average_expense_day = total_expense_month / total_duration  # 计算日平均支出
money_sun = money.sum()  # 计算不记收支的金额

max_expense_day = zfb_app.loc[zfb_app["支出金额"] == max_expense, "交易时间"].dt.strftime("%y年%m月%d日").iloc[
    0]  # 最大支出的交易日期
min_expense_day = zfb_app.loc[zfb_app["支出金额"] == min_expense, "交易时间"].dt.strftime("%y年%m月%d日").iloc[
    0]  # 最小支出的交易日期
max_income_day = zfb_app.loc[zfb_app["收入金额"] == max_income, "交易时间"].dt.strftime("%y年%m月%d日").iloc[
    0]  # 最大收入的交易日期
min_income_day = zfb_app.loc[zfb_app["收入金额"] == min_income, "交易时间"].dt.strftime("%y年%m月%d日").iloc[
    0]  # 最小收入的交易日期

transaction_type_1 = ("支出" if earliest_row["收入金额"] == 0.00 else "收入")  # 确定最早交易的类型（支出或收入）
earliest = (earliest_row["支出金额"] if earliest_row["收入金额"] == 0.00 else earliest_row["收入金额"])  # 确定最早交易的金额
transaction_type_2 = ("支出" if latest_row["收入金额"] < 0 else "收入")  # 确定最晚交易的类型（支出或收入）
latest = (latest_row["支出金额"] if latest_row["收入金额"] == 0.00 else latest_row["收入金额"])  # 确定最晚交易的金额

max_expense_time = zfb_app.loc[zfb_app["支出金额"] == max_expense, "交易时间"].dt.strftime("%y年%m月%d日%H:%M:%S").iloc[
    0]  # 最大支出交易的时间
max_income_time = zfb_app.loc[zfb_app["收入金额"] == max_income, "交易时间"].dt.strftime("%y年%m月%d日%H:%M:%S").iloc[
    0]  # 最大收入交易的时间

mode_number = get_mode_info(expenses=zfb_app["支出金额"], incomes=zfb_app["收入金额"])  # 获取支出和收入的众数信息

# section 输出结果
print(
    f"在{total_duration}天里，你总共花费了{total_expense_month}元，平均每天花费{average_expense_day:.2f}元。\r\n"
    f"你总共收入了{total_income_month}元，平均每天收入{average_income_day:.2f}元。\r\n"
    f"不计收支的金额(支付宝转帐，退款，还款等)共为{money_sun}元。\r\n"
    f"花费最多的月份是{nan}，共{nan}元。"
    f"收入最多的月份是{nan}，共{nan}元。"
    f"{max_expense_day}是你花费最多的一天，花费了{max_expense}元；{min_expense_day}是你花费最少的一天，花费了{min_expense}元。\r\n"
    f"{max_income_day}是你收入最多的一天，收入了{max_income}元；{max_income_day}是你收入最少的一天，收入了{min_income}元。\r\n"
    f"最早的一笔交易是在{earliest_transaction_date.strftime('%y-%m-%d')}的{shi_jian_1} "
    f"{earliest_transaction_date.strftime('%H:%M:%S')}，你{transaction_type_1}了{earliest}元。\r\n"
    f"最晚的一笔交易是在{latest_transaction_date.strftime('%y-%m-%d')}的{shi_jian_2} "
    f"{latest_transaction_date.strftime('%H:%M:%S')}，你{transaction_type_2}了{latest}元。\r\n"
    f"\r\n"
    f"你花费最多的一笔交易是在{max_expense_time}，因为{max_expense_reason}，花费了{max_expense}元。\r\n"
    f"你收入最多的一笔交易是在{max_income_time}，因为{max_income_reason}，收入了{max_income}元。\r\n"
    f"{mode_number}"
)

# Section 尾注 开源许可证

# Bill_Analyzer © 2025 by ee19971 is licensed under Creative Commons Attribution 4.0 International
# https://creativecommons.org/licenses/by/4.0/
