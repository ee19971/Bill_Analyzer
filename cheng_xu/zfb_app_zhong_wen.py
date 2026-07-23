#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------

# @文件：zfb_app.py
# @时间：2025年02月16日09:43
# @作者：ee19971
# @邮箱：3504275453@qq.com
# @作用：统计支付宝APP中文版导出的账单信息

# ------------------------------------------------------------------------------
"""
支付宝APP中文版账单解析模块

解析支付宝APP导出的中文CSV账单文件（GB18030编码），生成统计报告。
"""
import pandas as pd
from decimal import Decimal
from .gong_yong_han_shu import (
    clean_amount,
    get_mode_info,
    search_file_line,
    calculate_financial_extremes,
    decimal_sum,
    format_decimal,
    extract_transaction_date_info,
    get_transaction_type_and_amount,
    build_monthly_summary,
)


def zfb_app_zhong_wen_csv(file_path: str) -> str:
    """解析支付宝APP中文版账单文件并生成统计报告

    Args:
        file_path (str): 支付宝APP账单文件路径（支持CSV和Excel格式）

    Returns:
        str: 包含统计结果的格式化字符串

    Note:
        支付宝APP账单特点：
        - 文件头部有摘要行（笔记录/收入/支出/不计收支）
        - 金额统一在"金额"列，需根据"收/支"列拆分
        - 末尾可能有一个无用的 'Unnamed: 12' 列
    """
    # --- 解析文件头部摘要信息 ---
    # Excel文件用空格分隔，搜索时不带逗号；CSV文件用逗号分隔
    is_excel = file_path.lower().endswith(('.xlsx', '.xls'))
    header_keyword = '交易时间' if is_excel else '交易时间,'

    header_result = search_file_line(file_path, header_keyword)
    if not header_result:
        # 尝试检测是否是网页版账单
        web_check = search_file_line(file_path, '发生时间')
        if web_check:
            raise ValueError("此文件是支付宝网页版账单，请选择「支付宝网页导出」类型")
        raise ValueError("未找到表头行，请检查文件格式或选择正确的账单类型")
    header_offset = header_result[0]['line'] - 1

    record_result = search_file_line(file_path, '笔记录')
    _record_info = record_result[0]['content'] if record_result else ''

    income_result = search_file_line(file_path, '收入')
    _income_info = income_result[0]['content'] if income_result else ''

    expense_result = search_file_line(file_path, '支出')
    _expense_info = expense_result[0]['content'] if expense_result else ''

    neutral_result = search_file_line(file_path, '不计收支')
    _neutral_info = neutral_result[0]['content'] if neutral_result else ''

    # --- 数据读取与清洗 ---
    if is_excel:
        df = pd.read_excel(file_path, skiprows=header_offset)
    else:
        df = pd.read_csv(file_path, skiprows=header_offset, encoding='GB18030')

    # 删除无用列
    if 'Unnamed: 12' in df.columns:
        df.drop(columns='Unnamed: 12', inplace=True)

    # 转换时间列
    df["交易时间"] = pd.to_datetime(df["交易时间"], errors="coerce")
    df.dropna(subset=["交易时间"], inplace=True)

    # --- 金额拆分 ---
    df["金额"] = df["金额"].apply(clean_amount)

    mask_income = df["收/支"] == "收入"
    mask_expense = df["收/支"] == "支出"

    df["收入金额"] = df["金额"].where(mask_income, Decimal(0))
    df["支出金额"] = (-df["金额"].apply(lambda x: x.copy_abs())).where(mask_expense, Decimal(0))
    df.loc[mask_income | mask_expense, "金额"] = Decimal(0)

    # 按交易时间排序
    df["交易时间日"] = df["交易时间"].dt.strftime("%H:%M:%S")
    df = df.sort_values(by="交易时间日")

    # 填充空值
    text_cols = ['商品说明', '收/付款方式', '备注', '商家订单号']
    numeric_cols = ['金额', '收入金额', '支出金额']
    df[text_cols] = df[text_cols].fillna("")
    df[numeric_cols] = df[numeric_cols].fillna(Decimal(0))

    # --- 数值统计 ---
    total_days = (df["交易时间"].max() - df["交易时间"].min()).days
    if total_days == 0:
        total_days = 1  # 防止除以零

    expense_col = "支出金额"
    income_col = "收入金额"

    # 极值分析
    extremes = calculate_financial_extremes(
        df=df, name_col="商品说明", type_col="交易分类", remark_col="备注",
        expense_col=expense_col, income_col=income_col
    )
    max_expense = format_decimal(extremes['max_expense']['amount'])
    min_expense = format_decimal(extremes['min_expense']['amount'])
    max_income = format_decimal(extremes['max_income']['amount'])
    min_income = format_decimal(extremes['min_income']['amount'])

    # 收支汇总
    total_expense = decimal_sum(df[expense_col])
    avg_daily_expense = format_decimal(total_expense / Decimal(total_days))
    total_income = decimal_sum(df[income_col])
    avg_daily_income = format_decimal(total_income / Decimal(total_days))
    neutral_total = decimal_sum(df["金额"])

    # 日期信息提取
    date_info = extract_transaction_date_info(df, "交易时间", expense_col, income_col)

    # 最早/最晚交易详情
    tx_type_1, tx_amount_1 = get_transaction_type_and_amount(
        date_info["earliest_row"], expense_col, income_col
    )
    tx_type_2, tx_amount_2 = get_transaction_type_and_amount(
        date_info["latest_row"], expense_col, income_col
    )

    # 众数
    mode_info = get_mode_info(expenses=df[expense_col], incomes=df[income_col])

    # 月度汇总
    monthly = build_monthly_summary(df, "交易时间", expense_col, income_col)
    max_expense_month_amount = format_decimal(monthly["max_expense_month_amount"])
    max_income_month_amount = format_decimal(monthly["max_income_month_amount"])

    # --- 生成报告 ---
    return (
        f"在{total_days}天里，你总共花费了{total_expense}元，"
        f"平均每天花费{avg_daily_expense}元。\n"
        f"你总共收入了{total_income}元，"
        f"平均每天收入{avg_daily_income}元。\n"
        f"不计收支的金额(部分账单如：充值提现、账户转存或者个人设置收支等"
        f"不计入为收入或者支出，记为不计收支类)共为{neutral_total}元。\n"
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
