#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------

# @文件：zfb_wy.py
# @时间：2025年02月16日09:43
# @作者：ee19971
# @邮箱：3504275453@qq.com
# @作用：统计支付宝网页版导出的账单信息

# ------------------------------------------------------------------------------
"""
支付宝网页版账单解析模块

解析支付宝网页版导出的CSV账单文件（GB18030编码），生成统计报告。
"""
import pandas as pd
from decimal import Decimal
from .gong_yong_han_shu import (
    get_time_period,
    get_mode_info,
    calculate_financial_extremes,
    format_decimal,
    extract_transaction_date_info,
    get_transaction_type_and_amount,
)


def zfb_wy_csv(file_path: str) -> str:
    """解析支付宝网页版账单CSV文件并生成统计报告

    Args:
        file_path (str): 支付宝网页版账单CSV文件路径（GB18030编码）

    Returns:
        str: 包含统计结果的格式化字符串

    Note:
        支付宝网页版账单特点：
        - 前4行为摘要信息，实际数据从第5行开始
        - 金额列已分为"支出金额（-元）"和"收入金额（+元）"两列
    """
    # --- 数据读取（跳过前4行摘要） ---
    zfb = pd.read_csv(file_path, encoding="gb18030", skiprows=4)

    # --- 数据清洗 ---
    zfb["发生时间"] = pd.to_datetime(zfb["发生时间"], errors="coerce")
    zfb = zfb.dropna(subset=["发生时间"])

    # 按时间排序
    zfb["发生时间1"] = zfb["发生时间"].dt.strftime("%H:%M:%S")
    zfb = zfb.sort_values(by="发生时间1")

    # --- 数值统计 ---
    total_days = (zfb["发生时间"].max() - zfb["发生时间"].min()).days
    if total_days == 0:
        total_days = 1  # 防止除以零

    expense_col = "支出金额（-元）"
    income_col = "收入金额（+元）"

    # 使用 Decimal 精度计算日均（修复原来硬编码 /31 的问题）
    total_expense = Decimal(str(zfb[expense_col].sum()))
    total_income = Decimal(str(zfb[income_col].sum()))
    avg_daily_expense = format_decimal(total_expense / Decimal(total_days))
    avg_daily_income = format_decimal(total_income / Decimal(total_days))

    # 极值分析
    extremes = calculate_financial_extremes(zfb, "商品名称", "业务类型", "备注")
    max_expense = format_decimal(extremes['max_expense']['amount'])
    min_expense = format_decimal(extremes['min_expense']['amount'])
    max_income = format_decimal(extremes['max_income']['amount'])
    min_income = format_decimal(extremes['min_income']['amount'])

    # 日期信息提取
    date_info = extract_transaction_date_info(zfb, "发生时间", expense_col, income_col)

    # 最早/最晚交易详情
    tx_type_1, tx_amount_1 = get_transaction_type_and_amount(
        date_info["earliest_row"], expense_col, income_col
    )
    tx_type_2, tx_amount_2 = get_transaction_type_and_amount(
        date_info["latest_row"], expense_col, income_col
    )

    # 众数
    mode_info = get_mode_info(zfb[expense_col], zfb[income_col])

    # --- 生成报告 ---
    return (
        f"在{total_days}天里，你总共花费了{total_expense}元，"
        f"平均每天花费{avg_daily_expense}元。\n"
        f"你总共收入了{total_income}元，"
        f"平均每天收入{avg_daily_income}元。\n"
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
