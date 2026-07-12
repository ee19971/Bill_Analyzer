#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------

# @文件：wx.py
# @时间：2025年02月25日16:09
# @作者：ee19971
# @邮箱：3504275453@qq.com
# @作用：Bill_Analyzer项目 - 统计微信导出的账单信息

# ------------------------------------------------------------------------------
"""
微信账单解析模块

解析微信APP导出的CSV账单文件，生成统计报告。
"""
import pandas as pd
from decimal import Decimal
from .gong_yong_han_shu import (
    get_time_period,
    get_mode_info,
    search_file_line,
    calculate_financial_extremes,
    clean_amount,
    decimal_sum,
    format_decimal,
    extract_transaction_date_info,
    get_transaction_type_and_amount,
    build_monthly_summary,
)


def _fix_shifted_rows(wx: pd.DataFrame) -> pd.DataFrame:
    """修复微信账单中因 '/' 导致的列错位问题

    当"收/支"列为 '/' 时，后续列数据会整体错位，
    此函数将错位的行进行左移修正。

    Args:
        wx: 原始微信账单DataFrame

    Returns:
        pd.DataFrame: 修复后的DataFrame
    """
    rows_to_update = []

    for index, row in wx.iterrows():
        col_value = row.get("Unnamed: 11")
        if pd.notna(col_value) and "￥" not in str(row.get("金额(元)", "")):
            if "/" in str(row.get("收/支", "")):
                # 列数据整体左移一位以修正错位
                rows_to_update.append((
                    index,
                    str(row["收/支"]).replace('/', ''),  # 收/支
                    row["金额(元)"],                       # 金额
                    row["支付方式"],                       # 支付方式
                    row["当前状态"],                       # 当前状态
                    row["交易单号"],                       # 交易单号
                    row["商户单号"],                       # 商户单号
                    row["备注"],                           # 备注
                ))

    # 批量更新修复后的数据
    columns = ["收/支", "金额(元)", "支付方式", "当前状态", "交易单号", "商户单号", "备注"]
    for index, *values in rows_to_update:
        for col, val in zip(columns, values):
            wx.at[index, col] = val

    return wx


def wx_csv(file_path: str) -> str:
    """解析微信支付账单CSV文件并生成统计报告

    Args:
        file_path (str): 微信账单CSV文件路径，需符合微信官方导出格式

    Returns:
        str: 包含统计结果的格式化字符串，涵盖总收支、极值交易、时间分布等

    Raises:
        IndexError: CSV文件中缺失关键字段
        UnicodeDecodeError: 文件编码异常
        KeyError: CSV列名与预期不符
    """
    # --- 解析文件头部统计信息 ---
    header_offset = search_file_line(file_path, '交易时间,', 'utf-8')[0]['line'] - 1
    record_count = search_file_line(file_path, '笔记录', 'utf-8')[0]['numbers']
    income_count = search_file_line(file_path, '收入：', 'utf-8')[0]['numbers']
    expense_count = search_file_line(file_path, '支出：', 'utf-8')[0]['numbers']
    neutral_count = search_file_line(file_path, '中性交易：', 'utf-8')[0]['numbers']

    # --- 数据读取与清洗 ---
    wx = pd.read_csv(file_path, skiprows=header_offset)

    # 修复列错位问题
    wx = _fix_shifted_rows(wx)

    # 删除无用列
    if "Unnamed: 11" in wx.columns:
        wx.drop(columns=["Unnamed: 11"], inplace=True)

    # 转换时间列并清除无效行
    wx["交易时间"] = pd.to_datetime(wx["交易时间"], errors='coerce')
    wx.dropna(subset=["交易时间"], inplace=True)

    # 将 '/' 标记为中性交易
    wx["收/支"] = wx["收/支"].str.replace('/', '中性交易')

    # 检查金额列是否存在数据错位
    if wx["金额(元)"].str.contains("收入").any() or wx["金额(元)"].str.contains("支出").any():
        print("存在收入或支出字段，请检查数据")

    # --- 金额拆分 ---
    wx["金额(元)"] = wx["金额(元)"].apply(clean_amount)

    mask_income = wx["收/支"] == "收入"
    mask_expense = wx["收/支"] == "支出"

    # 创建独立的收入/支出金额列
    wx["收入金额"] = wx["金额(元)"].where(mask_income, Decimal(0))
    wx["支出金额"] = (-wx["金额(元)"].apply(lambda x: x.copy_abs())).where(mask_expense, Decimal(0))
    wx.loc[mask_income | mask_expense, "金额(元)"] = Decimal(0)

    # 按交易时间排序
    wx["交易时间日"] = wx["交易时间"].dt.strftime("%H:%M:%S")
    wx = wx.sort_values(by="交易时间日")

    # --- 数值统计 ---
    total_days = (wx["交易时间"].max() - wx["交易时间"].min()).days
    if total_days == 0:
        total_days = 1  # 防止除以零

    # 极值分析
    extremes = calculate_financial_extremes(
        df=wx, name_col="商品", type_col="交易类型", remark_col="备注",
        expense_col="支出金额", income_col="收入金额"
    )
    max_expense = format_decimal(extremes['max_expense']['amount'])
    min_expense = format_decimal(extremes['min_expense']['amount'])
    max_income = format_decimal(extremes['max_income']['amount'])
    min_income = format_decimal(extremes['min_income']['amount'])

    # 收支汇总
    total_expense = decimal_sum(wx["支出金额"])
    avg_daily_expense = format_decimal(total_expense / Decimal(total_days))
    total_income = decimal_sum(wx["收入金额"])
    avg_daily_income = format_decimal(total_income / Decimal(total_days))
    neutral_total = decimal_sum(wx["金额(元)"])

    # 日期信息提取
    date_info = extract_transaction_date_info(wx, "交易时间", "支出金额", "收入金额")

    # 最早/最晚交易详情
    tx_type_1, tx_amount_1 = get_transaction_type_and_amount(date_info["earliest_row"], "支出金额", "收入金额")
    tx_type_2, tx_amount_2 = get_transaction_type_and_amount(date_info["latest_row"], "支出金额", "收入金额")

    # 众数
    mode_info = get_mode_info(expenses=wx["支出金额"], incomes=wx["收入金额"])

    # 月度汇总
    monthly = build_monthly_summary(wx, "交易时间", "支出金额", "收入金额")
    max_expense_month_amount = format_decimal(monthly["max_expense_month_amount"])
    max_income_month_amount = format_decimal(monthly["max_income_month_amount"])

    # --- 生成报告 ---
    return (
        f"在{total_days}天里，你有{int(expense_count[0])}笔支出共花费了{total_expense}元，"
        f"平均每天花费{avg_daily_expense}元。\n"
        f"你有{int(income_count[0])}笔收入总共{total_income}元，"
        f"平均每天收入{avg_daily_income}元。\n"
        f"不计收支的金额(充值/提现/理财通购买/零钱通存取/信用卡还款等交易)有"
        f"{int(neutral_count[0])}笔共为{neutral_total}元。\n"
        f"花费最多的月份是{monthly['max_expense_month']}，共{max_expense_month_amount}元。\n"
        f"收入最多的月份是{monthly['max_income_month']}，共{max_income_month_amount}元。\n"
        f"{date_info['max_expense_date']}是你花费最多的一天，花费了{max_expense}元；"
        f"{date_info['min_expense_date']}是你花费最少的一天，花费了{min_expense}元。\n"
        f"{date_info['max_income_date']}是你收入最多的一天，收入了{max_income}元；"
        f"{date_info['min_income_date']}是你收入最少的一天，收入了{min_income}元。\n"
        f"最早的一笔交易是在{date_info['earliest_date'].strftime('%y-%m-%d')}的"
        f"{date_info['earliest_period']} {date_info['earliest_date'].strftime('%H:%M:%S')}，"
        f"你{tx_type_1}了{tx_amount_1}元。\n"
        f"最晚的一笔交易是在{date_info['latest_date'].strftime('%y-%m-%d')}的"
        f"{date_info['latest_period']} {date_info['latest_date'].strftime('%H:%M:%S')}，"
        f"你{tx_type_2}了{tx_amount_2}元。\n"
        f"\n"
        f"你花费最多的一笔交易是在{date_info['max_expense_time']}，"
        f"因为{extremes['max_expense']['reason']}，花费了{max_expense}元。\n"
        f"你收入最多的一笔交易是在{date_info['max_income_time']}，"
        f"因为{extremes['max_income']['reason']}，收入了{max_income}元。\n"
        f"{mode_info}。"
    )


# Section 尾注 开源许可证

# Bill_Analyzer © 2025 by ee19971 is licensed under Creative Commons Attribution 4.0 International
# https://creativecommons.org/licenses/by/4.0/
