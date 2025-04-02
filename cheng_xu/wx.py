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
from .gong_yong_han_shu import (get_time_period, nan, get_mode_info,
                                search_file_line, calculate_financial_extremes,
                                clean_amount, decimal_sum)


def wx_csv(file_path: str) -> str:
    """解析微信支付账单CSV文件并生成统计报告。

        该函数用于处理微信导出的账单CSV文件，统计收支数据、交易时间分布、极值交易等信息，
        并生成格式化的分析报告。

        Args:
            file_path (str): 微信账单CSV文件路径。文件需符合微信官方导出格式，
                应包含以下关键列：交易时间、收/支、金额(元)、商品、交易类型、备注等。

        Returns:
            str: 包含统计结果的格式化字符串，涵盖以下内容：
                - 总收支金额及日均值
                - 极值交易（最高/最低收入/支出）
                - 交易时间分布特征
                - 特殊交易类型统计

        Raises:
            IndexError: 如果CSV文件中缺失关键字段（如'交易时间'、'收入'、'支出'等）
            UnicodeDecodeError: 文件编码非UTF-8且自动检测失败时可能抛出
            KeyError: CSV列名与预期不符时可能抛出

        Notes:
            - 依赖 `gong_yong_han_shu` 模块中的工具函数
            - 金额处理使用 Decimal 类型保证精度
            - 会自动处理微信账单的格式异常（如金额列错位）

        示例文件结构要求：
            ┌───────────┬───────┬───────────┬───
            │ 交易时间   │ 收/支 │ 金额(元)  │ ...
            ├───────────┼───────┼───────────┼───
            │ 2023-01-01│ 支出  │  -100.00  │
            │ 2023-01-02│ 收入  │   500.00  │
            └───────────┴───────┴───────────┴───
        """
    # Section 常量
    fmt = lambda d: d.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)  # 格式化金额
    spike = search_file_line(file_path, '交易时间,', 'utf-8')[0]['line'] - 1  # 查找数据开始行的位置
    zhong_ji_lu = search_file_line(file_path, '笔记录', 'utf-8')[0]['numbers']  # 查找并提取笔记录信息
    shou_ru = search_file_line(file_path, '收入：', 'utf-8')[0]['numbers']  # 查找并提取收入信息
    zhi_chu = search_file_line(file_path, '支出：', 'utf-8')[0]['numbers']  # 查找并提取支出信息
    zhong_xing_jiao_yi = search_file_line(file_path, '中性交易：', 'utf-8')[0]['numbers']  # 查找并提取中性交易信息
    # Section 数据清洗
    wx = pd.read_csv(file_path, skiprows=spike)

    # --- 数据清洗阶段 ---
    # 处理微信账单格式错乱问题（金额列可能包含非金额数据）
    # 典型场景：当"收/支"列为 '/' 时，后续列数据会整体错位
    rows_to_update = []

    for index, row in wx.iterrows():
        i = row["Unnamed: 11"]
        if pd.notna(i):
            if "￥" not in row["金额(元)"]:# 检测金额列是否包含有效货币符号
                if "/" in row["收/支"]:# 当'收/支'列为'/'时触发修复逻辑
                    # 列数据整体左移：金额列 → 收/支列，支付方式列 → 金额列，依此类推
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
                        (index, new_收_支, new_金额_元, new_支付方式, new_当前状态, new_交易单号, new_商户单号,
                         new_备注))

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

    max_expense_day = wx.loc[wx["支出金额"] == max_expense, "交易时间"].dt.strftime("%y年%m月%d日").iloc[
        0]  # 获取最大支出金额对应的日期
    max_income_day = wx.loc[wx["收入金额"] == max_income, "交易时间"].dt.strftime("%y年%m月%d日").iloc[
        0]  # 获取最大收入金额对应的日期
    min_expense_day = wx.loc[wx["支出金额"] == min_expense, "交易时间"].dt.strftime("%y年%m月%d日").iloc[
        0]  # 获取最小支出金额对应的日期
    min_income_day = wx.loc[wx["收入金额"] == min_income, "交易时间"].dt.strftime("%y年%m月%d日").iloc[
        0]  # 获取最小收入金额对应的日期
    transaction_type_1 = ("支出" if earliest_row["收入金额"] == 0.00 else "收入")  # 确定最早交易的类型（支出或收入）
    earliest = (earliest_row["支出金额"] if earliest_row["收入金额"] == 0.00 else earliest_row["收入金额"])  # 确定最早交易的金额
    transaction_type_2 = ("支出" if latest_row["收入金额"] < 0 else "收入")  # 确定最晚交易的类型（支出或收入）
    latest = (latest_row["支出金额"] if latest_row["收入金额"] == 0.00 else latest_row["收入金额"])  # 确定最晚交易的金额

    max_expense_time = wx.loc[wx["支出金额"] == max_expense, "交易时间"].dt.strftime("%y年%m月%d日%H:%M:%S").iloc[
        0]  # 最大支出交易的时间
    max_income_time = wx.loc[wx["收入金额"] == max_income, "交易时间"].dt.strftime("%y年%m月%d日%H:%M:%S").iloc[
        0]  # 最大收入交易的时间

    # 获取支出和收入的众数信息
    mode_number = get_mode_info(expenses=wx["支出金额"], incomes=wx["收入金额"])

    # 按月份统计支出和收入
    wx["交易月"] = wx["交易时间"].dt.to_period("M")  # 提取交易时间的年月信息
    # 按月份统计支出和收入
    monthly_summary = (
        wx.groupby("交易月").agg(
            总支出=("支出金额", "sum"),
            总收入=("收入金额", "sum"))
        .reset_index())
    # 找到支出最多的月份
    max_expense_month = monthly_summary.loc[monthly_summary["总支出"].idxmin()]
    max_expense_month_str = max_expense_month["交易月"].strftime("%Y-%m")
    max_expense_month_amount = fmt(max_expense_month["总支出"])
    # 找到收入最多的月份
    min_income_month = monthly_summary.loc[monthly_summary["总收入"].idxmax()]
    min_income_month_str = min_income_month["交易月"].strftime("%Y-%m")
    min_income_month_amount = fmt(min_income_month["总收入"])

    # section 输出结果
    return (
        f"在{total_duration}天里，你有{int(zhi_chu[0])}笔支出共花费了{total_expense_year}元，平均每天花费{average_expense_day}元。\n"
        f"你有{int(shou_ru[0])}笔收入总共{total_income_year}元，平均每天收入{average_income_day}元。\n"
        f"不计收支的金额(充值/提现/理财通购买/零钱通存取/信用卡还款等交易)有{int(zhong_xing_jiao_yi[0])}笔共为{money_sun}元。\n"
        f"花费最多的月份是{max_expense_month_str}，共{max_expense_month_amount}元。\n"
        f"收入最多的月份是{min_income_month_str}，共{min_income_month_amount}元。\n"
        f"{max_expense_day}是你花费最多的一天，花费了{max_expense}元；{min_expense_day}是你花费最少的一天，花费了{min_expense}元。\n"
        f"{max_income_day}是你收入最多的一天，收入了{max_income}元；{max_income_day}是你收入最少的一天，收入了{min_income}元。\n"
        f"最早的一笔交易是在{earliest_transaction_date.strftime('%y-%m-%d')}的{shi_jian_1} "
        f"{earliest_transaction_date.strftime('%H:%M:%S')}，你{transaction_type_1}了{earliest}元。\n"
        f"最晚的一笔交易是在{latest_transaction_date.strftime('%y-%m-%d')}的{shi_jian_2} "
        f"{latest_transaction_date.strftime('%H:%M:%S')}，你{transaction_type_2}了{latest}元。\n"
        f"\n"
        f"你花费最多的一笔交易是在{max_expense_time}，因为{max_expense_reason}，花费了{max_expense}元。\n"
        f"你收入最多的一笔交易是在{max_income_time}，因为{max_income_reason}，收入了{max_income}元。\n"
        f"{mode_number}。"
    )

# Section 尾注 开源许可证

# Bill_Analyzer © 2025 by ee19971 is licensed under Creative Commons Attribution 4.0 International
# https://creativecommons.org/licenses/by/4.0/
