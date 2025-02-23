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

nan = "___" # 开发时占位用的空值


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


def calculate_financial_extremes(
        df: DataFrame, name_col: str, type_col: str, remark_col: str,
        expense_col: str = "支出金额（-元）",
        income_col: str = "收入金额（+元）"
) -> Dict[str, Dict[str, Any]]:
    """
    计算支付宝账单的收支极值（支持APP/网页双版）

    Args:
        df (pd.DataFrame): 包含财务数据的DataFrame，必须包含以下列：
            - 交易时间（datetime类型）
            - 金额相关列（数值类型）
        name_col (str): 商品说明/商品名称列名
        type_col (str): 交易分类/业务类型列名
        remark_col (str): 备注列名
        expense_col (str, optional): 支出金额列名，默认适用于网页版
        income_col (str, optional): 收入金额列名，默认适用于网页版

    Returns:
        Dict[str, Dict[str, Any]]: 包含极值信息的字典，结构示例：
        {
            "max_expense": {
                "amount": 284.0,
                "reason": "电动车电池,数码电器,换购新电池"},
            "min_expense": {
                "amount": -0.03,
                "reason": "余额宝收益,理财收益,每日收益"},
            "max_income": {
                "amount": 159.0,
                "reason": "退款成功,交易关闭,商品退货"},
            "min_income": {
                "amount": 0.01,
                "reason": "余额宝收益,理财收益,小额收益"}
        }

    Raises:
        KeyError: 当传入的列名在DataFrame中不存在时
        ValueError: 当金额列包含非数值类型数据时

    Example:
        >>> df = pd.read_csv('alipay.csv')
        >>> extremes = calculate_financial_extremes(df, '商品说明', '交易分类', '备注')
        >>> print(extremes['max_expense']['amount'])
        284.0
    """
    def _get_extreme(data: DataFrame, amount_col: str, is_max: bool, is_income: bool) -> dict:
        """核心极值计算逻辑（解耦嵌套函数）"""
        if is_income:
            amount_col = income_col
        else:
            amount_col = expense_col
        try:
            # 根据收支类型过滤数据
            if is_income:
                filtered = data[data[amount_col] > 0]
                extreme_val = filtered[amount_col].max() if is_max else filtered[amount_col].min()
            else:
                filtered = data[data[amount_col] < 0]
                extreme_val = filtered[amount_col].min() if is_max else filtered[amount_col].max()

            # 处理空数据情况
            if filtered.empty:
                return {"amount": 0.0, "reason": ""}

            # 获取明细信息
            row = filtered.loc[filtered[amount_col] == extreme_val].iloc[0]
            details = [str(row[name_col]).strip(), str(row[type_col]).strip(), str(row[remark_col]).strip()]
            return {
                "amount": extreme_val if not is_income else extreme_val,
                "reason": ",".join(filter(None, details))
            }
        except Exception as e:
            print(f"极值计算异常: {str(e)}")
            return {"amount": 0.0, "reason": ""}

    # 主逻辑流程
    return {
        "max_expense": _get_extreme(df, "支出金额（-元）", is_max=True, is_income=False),
        "min_expense": _get_extreme(df, "支出金额（-元）", is_max=False, is_income=False),
        "max_income": _get_extreme(df, "收入金额（+元）", is_max=True, is_income=True),
        "min_income": _get_extreme(df, "收入金额（+元）", is_max=False, is_income=True)
    }


def search_file_line(filename: str, keyword: str, encoding: str = 'GB18030') -> list[dict[str, int]]:
    """
    在文本文件中搜索包含指定关键字的行

    Args:
        filename (str): 要搜索的目标文件路径
        keyword (str): 需要查找的关键字（区分大小写）
        encoding (str, optional): 文件编码格式，默认使用GB18030编码

    Returns:
        list[dict]: 包含匹配结果的字典列表，每个字典包含：
            - line (int): 行号（从1开始计数）
            - content (str): 该行的文本内容（去除首尾空白符）

    Raises:
        FileNotFoundError: 当指定文件不存在时
        UnicodeDecodeError: 当使用错误编码读取文件时

    Example:
        >>> results = search_file_line('server.log', 'ERROR')
        >>> print(results)
        [
            {'line': 45, 'content': '2023-05-01 14:22 ERROR: Connection timeout'},
            {'line': 78, 'content': '2023-05-01 15:17 ERROR: Database connection failed'}
        ]

    Note:
        - 适用于日志文件分析等场景
        - 匹配方式为简单字符串包含检测（非正则表达式）
        - 大文件建议使用逐行读取方式优化内存
    """
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
