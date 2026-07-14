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
账单分析工具包 - 公共函数模块

提供各账单处理器共用的工具函数，包括：
- 时间段划分
- 众数计算
- 金融极值分析
- 文件关键词搜索
- 金额清洗与高精度求和
"""
import re
import logging
from pandas import DataFrame
import pandas as pd
from typing import Dict, Any, List
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)


def find_csv_header_offset(file_path: str, encoding: str) -> int:
    """自动检测 CSV 文件中表头行之前需要跳过的行数

    通过搜索已知关键词（发生时间、交易时间、账务流水号）定位真正的列名行。

    Args:
        file_path: CSV 文件路径
        encoding: 文件编码

    Returns:
        int: 需要跳过的行数
    """
    header_keywords = ['交易时间', '发生时间', '账务流水号']
    for keyword in header_keywords:
        try:
            results = search_file_line(file_path, keyword, encoding)
            if results:
                return results[0]['line'] - 1
        except Exception:
            continue
    return 0


def get_time_period(hour: int) -> str:
    """根据小时数智能划分时间段

    将24小时制的时间点映射到符合中文表达习惯的时间段描述，
    用于金融交易时间分析场景。

    Args:
        hour (int): 小时数值，范围0-23

    Returns:
        str: 时间段描述，包含：凌晨/早上/上午/中午/下午/傍晚/晚上

    Raises:
        ValueError: 当输入值超出0-23范围时

    Example:
        >>> get_time_period(7)
        '早上'
        >>> get_time_period(13)
        '下午'
    """
    if not 0 <= hour <= 23:
        raise ValueError(f"小时数必须在0-23之间，收到: {hour}")

    periods = [
        (0, 6, "凌晨"),
        (6, 9, "早上"),
        (9, 12, "上午"),
        (12, 13, "中午"),
        (13, 18, "下午"),
        (18, 20, "傍晚"),
        (20, 24, "晚上"),
    ]
    for start, end, label in periods:
        if start <= hour < end:
            return label
    return "晚上"


def get_mode_info(expenses: pd.Series, incomes: pd.Series) -> str:
    """
    计算支出和收入金额列的众数及其出现次数，并返回结果字符串。

    该函数接受两个Pandas Series对象，分别代表支出金额和收入金额。
    它会计算每个Series的众数，并返回出现次数最多的金额及其出现次数。
    如果支出和收入的众数出现次数相同，则返回两者的信息。

    Args:
        expenses (pd.Series): 支出金额列，包含负数值。
        incomes (pd.Series): 收入金额列，包含正数值。

    Returns:
        str: 包含众数信息的字符串

    Raises:
        TypeError: 如果输入不是Pandas Series对象。

    Example:
        >>> expenses = pd.Series([-100, -50, -50, -20])
        >>> incomes = pd.Series([50, 50, 30, 20])
        >>> get_mode_info(expenses, incomes)
        '支出-50 出现了 2 次'
    """
    # 分别计算支出（负值）和收入（正值）的众数
    expense_mode_series = expenses[expenses < 0].mode()
    incomes_mode_series = incomes[incomes > 0].mode()

    expense_mode = expense_mode_series.iloc[0] if not expense_mode_series.empty else None
    incomes_mode = incomes_mode_series.iloc[0] if not incomes_mode_series.empty else None

    # 获取众数的出现次数
    expense_counts = expenses.value_counts().get(expense_mode, 0)
    incomes_counts = incomes.value_counts().get(incomes_mode, 0)

    # 构建结果字符串
    if expense_mode is not None and incomes_mode is not None:
        if expense_counts > incomes_counts:
            return f"支出{expense_mode} 出现了 {expense_counts} 次"
        elif incomes_counts > expense_counts:
            return f"收入{incomes_mode} 出现了 {incomes_counts} 次"
        else:
            return (
                f"支出金额 {expense_mode} 和收入金额 {incomes_mode} "
                f"出现次数相同，均为 {expense_counts} 次"
            )
    elif expense_mode is not None:
        return f"支出{expense_mode} 出现了 {expense_counts} 次"
    elif incomes_mode is not None:
        return f"收入{incomes_mode} 出现了 {incomes_counts} 次"
    else:
        return "没有有效的支出或收入金额"


def calculate_financial_extremes(
        df: pd.DataFrame,
        name_col: str,
        type_col: str,
        remark_col: str,
        expense_col: str = "支出金额（-元）",
        income_col: str = "收入金额（+元）"
) -> Dict[str, Dict[str, Any]]:
    """金融交易极值分析（支持多平台账单）

    识别账单中的典型收支特征，包括：
    - 最大/最小单笔支出
    - 最大/最小单笔收入
    - 关联交易描述信息

    Args:
        df (pd.DataFrame): 包含完整交易数据的DataFrame
        name_col (str): 商品/交易名称字段名
        type_col (str): 交易分类字段名
        remark_col (str): 备注信息字段名
        expense_col (str): 支出金额字段名，默认"支出金额（-元）"
        income_col (str): 收入金额字段名，默认"收入金额（+元）"

    Returns:
        Dict: 结构化极值分析结果，包含：
            - max_expense: 最大支出 {amount, reason}
            - min_expense: 最小支出
            - max_income: 最大收入
            - min_income: 最小收入
    """

    def _get_extreme(data: DataFrame, amount_col: str, is_max: bool, is_income: bool) -> dict:
        """核心极值计算逻辑

        Args:
            data: 交易数据DataFrame
            amount_col: 金额列名（会被 is_income 覆盖）
            is_max: 是否取最大值（False则取最小值）
            is_income: 是否为收入类型

        Returns:
            dict: {'amount': 极值金额, 'reason': 交易描述}
        """
        actual_col = income_col if is_income else expense_col
        try:
            # 根据收支类型过滤数据并计算极值
            if is_income:
                filtered = data[data[actual_col] > 0]
                extreme_val = filtered[actual_col].max() if is_max else filtered[actual_col].min()
            else:
                filtered = data[data[actual_col] < 0]
                extreme_val = filtered[actual_col].min() if is_max else filtered[actual_col].max()

            if filtered.empty:
                return {"amount": 0.0, "reason": ""}

            # 获取极值对应行的明细信息
            row = filtered.loc[filtered[actual_col] == extreme_val].iloc[0]
            details = [
                str(row[name_col]).strip(),
                str(row[type_col]).strip(),
                str(row[remark_col]).strip(),
            ]
            return {
                "amount": extreme_val,
                "reason": ",".join(filter(None, details)),
            }
        except Exception as e:
            logger.warning("极值计算异常: %s", e)
            return {"amount": 0.0, "reason": ""}

    return {
        "max_expense": _get_extreme(df, expense_col, is_max=True, is_income=False),
        "min_expense": _get_extreme(df, expense_col, is_max=False, is_income=False),
        "max_income": _get_extreme(df, income_col, is_max=True, is_income=True),
        "min_income": _get_extreme(df, income_col, is_max=False, is_income=True),
    }


def search_file_line(filename: str, keyword: str, encoding: str = 'GB18030') -> List[Dict[str, any]]:
    """增强版文件搜索函数（支持文本文件/Excel文件）

    在文件中搜索包含指定关键词的行，并提取行内所有数字。

    Args:
        filename (str): 文件路径，支持.csv/.xlsx/.xls
        keyword (str): 搜索关键词（区分大小写）
        encoding (str): 文本文件编码，默认GB18030

    Returns:
        List[Dict]: 匹配行列表，每项包含 line(行号), content(内容), numbers(数字列表)

    Raises:
        ValueError: 不支持的文件格式或Excel读取失败
    """
    results = []
    number_pattern = re.compile(r"[-+]?\d*\.\d+|\d+")

    if filename.lower().endswith(('.xlsx', '.xls')):
        # Excel文件处理：逐行拼接单元格并提取数字
        try:
            df = pd.read_excel(filename, header=None)
            for idx, row in df.iterrows():
                line_content = " ".join(str(cell) for cell in row)
                numbers = [float(n) for n in number_pattern.findall(line_content)]
                if keyword in line_content:
                    results.append({
                        'line': idx + 1,
                        'content': line_content.strip(),
                        'numbers': numbers,
                    })
        except Exception as e:
            raise ValueError(f"Excel文件读取失败: {str(e)}")

    elif filename.lower().endswith('.csv'):
        # 文本文件处理：按编码逐行读取
        with open(filename, 'r', encoding=encoding) as f:
            for line_num, line in enumerate(f, 1):
                if keyword in line:
                    numbers = [float(n) for n in number_pattern.findall(line)]
                    results.append({
                        'line': line_num,
                        'content': line.strip(),
                        'numbers': numbers,
                    })
    else:
        raise ValueError("不支持的文件格式，仅支持.csv/.xlsx/.xls")

    return results


def clean_amount(raw_value: Any) -> Decimal:
    """清洗并转换金额数据为高精度Decimal类型

    专为金融场景设计，处理包含货币符号、千分位分隔符等非数字字符的金额字符串。

    Args:
        raw_value (Any): 原始金额数据，可以是字符串/数字/空值等任意类型

    Returns:
        Decimal: 清洗后的Decimal数值，空值/无效值返回 Decimal(0)

    Example:
        >>> clean_amount("￥1,234.56")
        Decimal('1234.56')
        >>> clean_amount(None)
        Decimal('0')
    """
    try:
        # 移除所有非数字、负号和小数点字符
        cleaned = re.sub(r'[^\d\.-]', '', str(raw_value))
        return Decimal(cleaned) if cleaned and cleaned != "." else Decimal(0)
    except Exception:
        return Decimal(0)


def decimal_sum(series: pd.Series) -> Decimal:
    """高精度数值序列求和

    专为金融数据设计的精确求和方案，解决pandas默认浮点运算的精度问题。

    Args:
        series (pd.Series): 需要求和的数列，元素应为Decimal类型

    Returns:
        Decimal: 精确求和结果

    Example:
        >>> s = pd.Series([Decimal('0.1')]*10)
        >>> decimal_sum(s)
        Decimal('1.0')
    """
    return sum(filter(None, series), Decimal(0))


def format_decimal(value, places='0.00') -> Decimal:
    """将数值格式化为指定精度的Decimal

    Args:
        value: 需要格式化的数值（支持Decimal/float/int/str）
        places: 精度格式，默认'0.00'保留两位小数

    Returns:
        Decimal: 格式化后的Decimal数值
    """
    return Decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def extract_transaction_date_info(df: pd.DataFrame, time_col: str,
                                  expense_col: str, income_col: str) -> Dict:
    """提取交易日期相关的公共信息（最早/最晚交易、极值日期等）

    将各账单处理器中重复的日期提取逻辑统一到此函数。

    Args:
        df: 已排序的交易数据DataFrame
        time_col: 时间列名
        expense_col: 支出金额列名
        income_col: 收入金额列名

    Returns:
        Dict: 包含以下键的字典：
            - earliest_row / latest_row: 最早/最晚交易行
            - earliest_date / latest_date: 最早/最晚交易时间
            - earliest_period / latest_period: 最早/最晚交易时段
            - max_expense_date / min_expense_date: 支出极值日期
            - max_income_date / min_income_date: 收入极值日期
            - max_expense_time / max_income_time: 支出/收入极值完整时间
    """
    earliest_row = df.iloc[0]
    latest_row = df.iloc[-1]
    earliest_date = earliest_row[time_col]
    latest_date = latest_row[time_col]

    # 格式化极值对应的日期和时间
    max_expense_idx = df[expense_col].idxmin()  # 支出为负值，最小即最大支出
    min_expense_idx = df[expense_col].idxmax()  # 支出为负值，最大即最小支出
    max_income_idx = df[income_col].idxmax()
    min_income_idx = df[income_col].idxmin()

    return {
        "earliest_row": earliest_row,
        "latest_row": latest_row,
        "earliest_date": earliest_date,
        "latest_date": latest_date,
        "earliest_period": get_time_period(earliest_date.hour),
        "latest_period": get_time_period(latest_date.hour),
        "max_expense_date": df.loc[max_expense_idx, time_col].strftime("%y年%m月%d日"),
        "min_expense_date": df.loc[min_expense_idx, time_col].strftime("%y年%m月%d日"),
        "max_income_date": df.loc[max_income_idx, time_col].strftime("%y年%m月%d日"),
        "min_income_date": df.loc[min_income_idx, time_col].strftime("%y年%m月%d日"),
        "max_expense_time": df.loc[max_expense_idx, time_col].strftime("%y年%m月%d日%H:%M:%S"),
        "max_income_time": df.loc[max_income_idx, time_col].strftime("%y年%m月%d日%H:%M:%S"),
    }


def get_transaction_type_and_amount(row, expense_col: str, income_col: str):
    """根据收支金额判断交易类型和实际金额

    Args:
        row: DataFrame的一行数据
        expense_col: 支出金额列名
        income_col: 收入金额列名

    Returns:
        tuple: (交易类型字符串, 金额数值)
    """
    if row[income_col] == 0 or row[income_col] == Decimal(0):
        return "支出", row[expense_col]
    return "收入", row[income_col]


def build_monthly_summary(df: pd.DataFrame, time_col: str,
                          expense_col: str, income_col: str) -> Dict:
    """按月汇总收支数据并找出极值月份

    Args:
        df: 交易数据DataFrame
        time_col: 时间列名
        expense_col: 支出金额列名
        income_col: 收入金额列名

    Returns:
        Dict: 包含以下键：
            - max_expense_month: 支出最多月份的字符串 (如"2024-03")
            - max_expense_month_amount: 该月支出总额
            - max_income_month: 收入最多月份的字符串
            - max_income_month_amount: 该月收入总额
    """
    df_copy = df.copy()
    df_copy["交易月"] = df_copy[time_col].dt.to_period("M")

    monthly = (
        df_copy.groupby("交易月")
        .agg(总支出=(expense_col, "sum"), 总收入=(income_col, "sum"))
        .reset_index()
    )

    # 支出最多月份（支出为负值，idxmin即最大支出）
    max_exp_month = monthly.loc[monthly["总支出"].idxmin()]
    # 收入最多月份
    max_inc_month = monthly.loc[monthly["总收入"].idxmax()]

    return {
        "max_expense_month": max_exp_month["交易月"].strftime("%Y-%m"),
        "max_expense_month_amount": max_exp_month["总支出"],
        "max_income_month": max_inc_month["交易月"].strftime("%Y-%m"),
        "max_income_month_amount": max_inc_month["总收入"],
    }


# Section 尾注 开源许可证

# Bill_Analyzer © 2025 by ee19971 is licensed under Creative Commons Attribution 4.0 International
# https://creativecommons.org/licenses/by/4.0/
