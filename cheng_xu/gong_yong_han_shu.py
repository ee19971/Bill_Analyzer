#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------

# @文件：gong_yong_han_shu.py
# @时间：2025年02月16日09:19
# @作者：ee19971
# @邮箱：3504275453@qq.com
# @作用：程序会用到的公共函数

# ------------------------------------------------------------------------------
"""
账单分析工具包

包含以下模块：
- gong_yong_han_shu: 公共时间处理函数
- nan: 开发时占位用的空值
"""
from pandas import DataFrame
from typing import Dict, Any

nan = "___"


def get_time_period(hour):
    """
    根据给定的小时数返回时间段的描述。

    :param hour: 整数，表示一天中的小时数（0-23）
    :return: 字符串，表示时间段（如“凌晨”、“早上”等）
    """
    if 0 <= hour < 6:
        return "凌晨"
    elif 6 <= hour < 9:
        return "早上"
    elif 9 <= hour < 12:
        return "上午"
    elif hour == 12:
        return "中午"
    elif 13 <= hour < 18:
        return "下午"
    elif 18 <= hour < 20:
        return "傍晚"
    else:
        return "晚上"


def get_mode_info(expenses, incomes):
    """
    计算支出和收入的众数及其出现次数，并返回结果字符串。

    :param expenses: Pandas Series, 支出金额列
    :param incomes: Pandas Series, 收入金额列
    :return: str, 众数信息字符串
    """
    # 计算众数
    expense_mode_series = expenses[expenses < 0].mode()
    incomes_mode_series = incomes[incomes > 0].mode()

    # 检查众数是否存在
    if not expense_mode_series.empty:
        expense_mode = expense_mode_series.iloc[0]
    else:
        expense_mode = None

    if not incomes_mode_series.empty:
        incomes_mode = incomes_mode_series.iloc[0]
    else:
        incomes_mode = None

    # 使用 value_counts() 方法查看每个值的出现次数
    expense_value_counts = expenses.value_counts()
    incomes_value_counts = incomes.value_counts()

    # 获取众数的出现次数
    expense_Number_of_occurrences = expense_value_counts.get(expense_mode, 0)
    incomes_Number_of_occurrences = incomes_value_counts.get(incomes_mode, 0)

    # 构建结果字符串
    if expense_mode is not None and incomes_mode is not None:
        if expense_Number_of_occurrences > incomes_Number_of_occurrences:
            mode_number = (
                f"支出{expense_mode} 出现了 {expense_Number_of_occurrences} 次"
            )
        elif incomes_Number_of_occurrences > expense_Number_of_occurrences:
            mode_number = (
                f"收入{incomes_mode} 出现了 {incomes_Number_of_occurrences} 次"
            )
        else:
            mode_number = f"支出金额 {expense_mode} 和收入金额 {incomes_mode} 出现次数相同，均为 {expense_Number_of_occurrences} 次"
    elif expense_mode is not None:
        mode_number = f"支出{expense_mode} 出现了 {expense_Number_of_occurrences} 次"
    elif incomes_mode is not None:
        mode_number = f"收入{incomes_mode} 出现了 {incomes_Number_of_occurrences} 次"
    else:
        mode_number = "没有有效的支出或收入金额"

    return mode_number


def calculate_financial_extremes(df: DataFrame) -> Dict[str, Dict[str, Any]]:
    """计算支付宝账单的收支极值（通用函数版）"""

    def get_extreme_info(data, amount_col, is_income=False):
        """获取极值信息（内部函数）"""
        try:
            if is_income:
                filtered = data[data[amount_col] > 0]
                extreme = filtered[amount_col].max() if not filtered.empty else 0.00
            else:
                filtered = data[data[amount_col] < 0]
                extreme = filtered[amount_col].min() if not filtered.empty else 0.00

            row = data.loc[data[amount_col] == extreme].iloc[0] if not filtered.empty else None

            if row is not None:
                name = row["商品名称"].strip()
                type_ = row["业务类型"].strip()
                remark = row["备注"].strip()
                reason = f"{name}{',' if name else ' '}{type_},{remark}"
                return {"amount": abs(extreme), "reason": reason}
        except Exception as e:
            print(f"计算极值时发生错误：{str(e)}")
        return {"amount": 0.00, "reason": ""}

    return {
        "max_expense": get_extreme_info(df, "支出金额（-元）"),
        "min_expense": get_extreme_info(df, "支出金额（-元）", is_income=True),
        "max_income": get_extreme_info(df, "收入金额（+元）"),
        "min_income": get_extreme_info(df, "收入金额（+元）", is_income=True)
    }

def search_file_line(filename, keyword, encoding='GB18030'):
    """搜索文本文件返回包含关键字的行号"""
    results = []
    with open(filename, 'r', encoding=encoding) as f:
        for line_num, line in enumerate(f, 1):
            if keyword in line:
                results.append({
                    'line': line_num,
                    'content': line.strip()
                })
    return results

# Section 尾注 开源许可证

# Bill_Analyzer © 2025 by ee19971 is licensed under Creative Commons Attribution 4.0 International
# https://creativecommons.org/licenses/by/4.0/
