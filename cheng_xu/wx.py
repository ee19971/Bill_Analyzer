#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------

# @文件：wx.py
# @时间：2025年02月25日16:09
# @作者：ee19971
# @邮箱：3504275453@qq.com
# @作用：Bill_Analyzer项目${统计微信导出的账单信息}

# ------------------------------------------------------------------------------
# Section 导入包
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from gong_yong_han_shu import (get_time_period, nan, get_mode_info,
                               search_file_line, calculate_financial_extremes,
                               clean_amount, decimal_sum)

# Section 常量
fmt = lambda d: d.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)  # 格式化金额
filename = r'C:\test\Bill_Analyzer\微信支付账单.csv'  # 定义微信支付账单文件路径
spike = search_file_line(filename, '交易时间,', 'utf-8')[0]['line'] - 1  # 查找数据开始行的位置
ji_lu = search_file_line(filename, '笔记录', 'utf-8')[0]['content']  # 查找并提取笔记录信息
shou_ru = search_file_line(filename, '收入：', 'utf-8')[0]['content']  # 查找并提取收入信息
zhi_chu = search_file_line(filename, '支出：', 'utf-8')[0]['content']  # 查找并提取支出信息
zhong_xing_jiao_yi = search_file_line(filename, '中性交易：', 'utf-8')[0]['content']  # 查找并提取中性交易信息

# Section 数据清洗
wx = pd.read_csv(filename, skiprows=spike)

# 处理金额列没有金额的错误（这是微信账单的问题）
# 创建一个列表来存储需要更新的行
rows_to_update = []

for index, row in wx.iterrows():
    i = row["Unnamed: 11"]
    if pd.notna(i):
        if "￥" not in row["金额(元)"]:
            if "/" in row["收/支"]:
                # 删除 '收/支' 列中的 '/' 并将后面的值向前移动
                row["收/支"] = row["收/支"].replace('/', '')
                new_收_支 = row["金额(元)"]
                new_金额_元 = row["支付方式"]
                new_支付方式 = row["当前状态"]
                new_当前状态 = row["交易单号"]
                new_交易单号 = row["商户单号"]
                new_商户单号 = row["备注"]
                new_备注 = row["Unnamed: 11"]

                # 将新的值存储到列表中
                rows_to_update.append(
                    (index, new_收_支, new_金额_元, new_支付方式, new_当前状态, new_交易单号, new_商户单号, new_备注))

# 更新 DataFrame 中的列
for index, new_收_支, new_金额_元, new_支付方式, new_当前状态, new_交易单号, new_商户单号, new_备注 in rows_to_update:
    wx.at[index, "收/支"] = new_收_支
    wx.at[index, "金额(元)"] = new_金额_元
    wx.at[index, "支付方式"] = new_支付方式
    wx.at[index, "当前状态"] = new_当前状态
    wx.at[index, "交易单号"] = new_交易单号
    wx.at[index, "商户单号"] = new_商户单号
    wx.at[index, "备注"] = new_备注

# 删除没用的东西
wx.drop(columns=["Unnamed: 11"], inplace=True)  # 删除名为 "Unnamed: 11" 的列
wx["交易时间"] = pd.to_datetime(wx["交易时间"], errors='coerce')  # 将 "交易时间" 列转换为日期时间格式，无法转换的值设为 NaT
wx.dropna(subset=["交易时间"], inplace=True)  # 删除 "交易时间" 列中包含 NaT 的行
# 检查错误
wx["收/支"] = wx["收/支"].str.replace('/', '中性交易')  # 将 "收/支" 列中的 '/' 替换为 '中性交易'
if wx["金额(元)"].str.contains("收入").any() or wx["金额(元)"].str.contains(
        "支出").any():  # 检查 "金额(元)" 列中是否包含 "收入" 或 "支出"
    print("存在收入或支出字段，请检查数据")  # 如果存在，打印提示信息

# 把金额列的内容按“收/支”列转到新列，如果是收入把金额转到“收入金额”列，如果是支出转到“支出金额”列
wx["金额(元)"] = wx["金额(元)"].apply(clean_amount)

# 创建布尔掩码（mask）标识符合条件的数据行
mask_income = wx["收/支"] == "收入"  # 标记所有"收入"行
mask_expense = wx["收/支"] == "支出"  # 标记所有"支出"行
# 创建收入金额列（全Decimal操作）
wx["收入金额"] = wx["金额(元)"].where(
    mask_income,
    Decimal(0.00)
)
# 创建支出金额列（全Decimal操作）
wx["支出金额"] = (-wx["金额(元)"].apply(lambda x: x.copy_abs())).where(
    mask_expense,
    Decimal(0.00)
)  # 使用Decimal的绝对值方法
# 修改原始金额列（Decimal操作）
wx.loc[mask_income | mask_expense, "金额(元)"] = Decimal(0.00)
# ToDo:把‘/’转换为‘’

# 按'交易时间日'升序排列
wx["交易时间日"] = wx["交易时间"].dt.strftime("%H:%M:%S")
wx = wx.sort_values(by="交易时间日")

# section 处理数值
fmt = lambda d: d.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)  # 定义金额格式化函数，保留两位小数并四舍五入
total_duration = (wx["交易时间"].max() - wx["交易时间"].min()).days  # 计算账单时间范围的总天数（交易时间的最大值与最小值之差）

# 判断极值
extremes = calculate_financial_extremes(df=wx,
                                        name_col="商品",
                                        type_col="交易类型",
                                        remark_col="备注",
                                        expense_col="支出金额",
                                        income_col="收入金额")
max_expense = extremes['max_expense']['amount']  # 最大支出金额
max_expense_reason = extremes['max_expense']['reason']  # 最大支出的原因
min_expense = extremes['min_expense']['amount']  # 最小支出金额
max_income = extremes['max_income']['amount']  # 最大收入金额
max_income_reason = extremes['max_income']['reason']  # 最大收入的原因
min_income = extremes['min_income']['amount']  # 最小收入金额

total_expense_year = decimal_sum(wx["支出金额"])  # 计算全年总支出金额
average_expense_day = fmt(total_expense_year / Decimal(total_duration))  # 计算每日平均支出金额，保留两位小数
total_income_year = decimal_sum(wx["收入金额"])  # 计算全年总收入金额
average_income_day = fmt(total_income_year / Decimal(total_duration))  # 计算每日平均收入金额，保留两位小数
money_sun = decimal_sum(wx["金额(元)"])  # 计算不计收支的金额（如转账、退款等）总和

earliest_row = wx.iloc[0]  # 获取最早的一行数据
earliest_transaction_date = earliest_row["交易时间"]  # 获取最早交易的时间
shi_jian_1 = get_time_period(earliest_transaction_date.hour)  # 获取最早交易时间的时段
latest_row = wx.iloc[-1]  # 获取最晚的一行数据
latest_transaction_date = latest_row["交易时间"]  # 获取最晚交易的时间
shi_jian_2 = get_time_period(latest_transaction_date.hour)  # 获取最晚交易时间的时段

max_expense = fmt(Decimal(max_expense))
min_expense = fmt(Decimal(min_expense))
max_income = fmt(Decimal(max_income))
min_income = fmt(Decimal(min_income))

max_expense_day = wx.loc[wx["支出金额"] == max_expense, "交易时间"].dt.strftime("%y年%m月%d日").iloc[0] # 获取最大支出金额对应的日期
max_income_day = wx.loc[wx["收入金额"] == max_income, "交易时间"].dt.strftime("%y年%m月%d日").iloc[0] # 获取最大收入金额对应的日期
min_expense_day = wx.loc[wx["支出金额"] == min_expense, "交易时间"].dt.strftime("%y年%m月%d日").iloc[0] # 获取最小支出金额对应的日期
min_income_day = wx.loc[wx["收入金额"] == min_income, "交易时间"].dt.strftime("%y年%m月%d日").iloc[0] # 获取最小收入金额对应的日期
transaction_type_1 = ("支出" if earliest_row["收入金额"] == 0.00 else "收入")  # 确定最早交易的类型（支出或收入）
earliest = (earliest_row["支出金额"] if earliest_row["收入金额"] == 0.00 else earliest_row["收入金额"])  # 确定最早交易的金额
transaction_type_2 = ("支出" if latest_row["收入金额"] < 0 else "收入")  # 确定最晚交易的类型（支出或收入）
latest = (latest_row["支出金额"] if latest_row["收入金额"] == 0.00 else latest_row["收入金额"])  # 确定最晚交易的金额

max_expense_time = wx.loc[wx["支出金额"] == max_expense, "交易时间"].dt.strftime("%y年%m月%d日%H:%M:%S").iloc[
    0]  # 最大支出交易的时间
max_income_time = wx.loc[wx["收入金额"] == max_income, "交易时间"].dt.strftime("%y年%m月%d日%H:%M:%S").iloc[
    0]  # 最大收入交易的时间

mode_number = get_mode_info(expenses=wx["支出金额"], incomes=wx["收入金额"])  # 获取支出和收入的众数信息

# section 输出结果
print(
    f"在{total_duration}天里，你总共花费了{total_expense_year}元，平均每天花费{average_expense_day}元。\r\n"
    f"你总共收入了{total_income_year}元，平均每天收入{average_income_day}元。\r\n"
    f"不计收支的金额(充值/提现/理财通购买/零钱通存取/信用卡还款等交易)共为{money_sun}元。\r\n"
    f"花费最多的月份是{nan}，共{nan}元。\r\n"
    f"收入最多的月份是{nan}，共{nan}元。\r\n"
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
