#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------

# @文件：ke_shi_hua.py
# @时间：2025年04月06日08:57
# @作者：ee19971
# @邮箱：3504275453@qq.com
# @作用：Bill_Analyzer项目 - 账单可视化分析模块（日历热力图）

# ------------------------------------------------------------------------------
"""
账单可视化模块

基于 Plotly 生成日历热力图，展示每日收支金额分布。
使用稀疏矩阵优化大数据量下的内存占用。
"""
import os
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from scipy.sparse import csr_matrix
from plotly.offline import plot


# 月份中文映射常量
MONTH_NAMES = {
    1: "一月份", 2: "二月份", 3: "三月份", 4: "四月份",
    5: "五月份", 6: "六月份", 7: "七月份", 8: "八月份",
    9: "九月份", 10: "十月份", 11: "十一月份", 12: "十二月份",
}
MONTH_ORDER = list(MONTH_NAMES.values())


def load_data(filepath: str) -> pd.DataFrame:
    """优化内存的数据加载函数

    使用 dtype 指定和 category 类型减少内存占用，
    同时完成时间解析和金额计算。

    Args:
        filepath: CSV文件路径（GB18030编码）

    Returns:
        pd.DataFrame: 包含时间分解字段和金额的计算结果
    """
    dtype_spec = {
        '收入金额（+元）': 'float',
        '支出金额（-元）': 'float',
        '备注': 'category',
    }
    df = pd.read_csv(
        filepath,
        encoding="GB18030",
        header=0,
        usecols=['发生时间', '收入金额（+元）', '支出金额（-元）', '备注'],
        dtype=dtype_spec,
    )

    # 时间处理：解析并提取年/月/日字段
    df["发生时间"] = pd.to_datetime(df["发生时间"], format='%Y/%m/%d %H:%M', cache=True)
    df["Year"] = df["发生时间"].dt.year
    df["Month"] = df["发生时间"].dt.month.map(MONTH_NAMES).astype('category')
    df["Day"] = df["发生时间"].dt.day.astype('int8')

    # 计算净金额（收入+支出，支出为负值）
    df["金额"] = df["收入金额（+元）"] + df["支出金额（-元）"]
    return df


def create_sparse_pivot(dataframe: pd.DataFrame) -> pd.DataFrame:
    """生成稀疏矩阵透视表以优化内存

    将月份×日期的金额数据转换为稀疏矩阵格式，
    适用于大量零值数据的场景。

    Args:
        dataframe: 包含 Month/Day/金额 字段的DataFrame

    Returns:
        pd.DataFrame: 月份×日期的稀疏DataFrame
    """
    day_order = range(1, 32)

    month_cat = pd.Categorical(dataframe['Month'], categories=MONTH_ORDER)
    day_cat = pd.Categorical(dataframe['Day'], categories=day_order)

    sparse_matrix = csr_matrix(
        (dataframe['金额'].values, (month_cat.codes, day_cat.codes)),
        shape=(len(MONTH_ORDER), len(day_order)),
    )

    return pd.DataFrame.sparse.from_spmatrix(
        sparse_matrix, index=MONTH_ORDER, columns=day_order
    )


def generate_hover_text(pivot_df: pd.DataFrame) -> list:
    """生成热力图悬停提示文本

    根据金额正负判断交易类型，生成格式化的HTML提示文本。

    Args:
        pivot_df: 月份×日期的透视DataFrame

    Returns:
        list: 二维列表，每个元素为对应单元格的HTML提示文本
    """
    # 使用 np.select 向量化判断交易类型
    conditions = [pivot_df > 0, pivot_df < 0, pivot_df == 0]
    trans_types = pd.DataFrame(
        np.select(conditions, ["收入", "支出", "无交易"], default="无交易").astype(str),
        index=pivot_df.index,
        columns=pivot_df.columns,
    )

    return [
        [
            f"月份：{month}<br>日期：{day}号<br>"
            f"类型：{trans_types.loc[month, day]}<br>"
            f"金额：{pivot_df.loc[month, day]:,.2f}元"
            for day in pivot_df.columns
        ]
        for month in pivot_df.index
    ]


def create_calendar_plot(dataframe: pd.DataFrame) -> go.Figure:
    """生成日历热力图

    Args:
        dataframe: 包含 Month/Day/金额/Year 字段的DataFrame

    Returns:
        go.Figure: Plotly热力图对象
    """
    pivot_df = create_sparse_pivot(dataframe)
    max_value = dataframe['金额'].max()
    min_value = dataframe['金额'].min()
    year = dataframe['Year'].iloc[0]

    fig = go.Figure(go.Heatmap(
        z=pivot_df.sparse.to_dense().values,
        x=[str(d) for d in pivot_df.columns],
        y=pivot_df.index,
        colorscale="Viridis",
        hoverinfo="text",
        text=generate_hover_text(pivot_df),
        zsmooth=False,
        zmin=min_value + 0.5,
        zmax=max_value,
        zmid=0,
    ))

    fig.update_layout(
        title=f"{year}年支付宝账户余额日历图",
        xaxis_title="日期",
        yaxis_title="月份",
        height=800,
        width=1200,
        dragmode='pan',
        xaxis=dict(
            tickvals=list(range(0, 31, 3)),
            ticktext=list(map(str, range(1, 32, 3))),
            rangeslider=dict(visible=True),
        ),
        yaxis=dict(
            tickmode="array",
            tickvals=pivot_df.index,
            range=[-0.5, 11.5],
            fixedrange=False,
            autorange=False,
        ),
    )

    # 标记最大收入和最大支出注释
    for extreme_type, label in [('max', '最大收入'), ('min', '最大支出')]:
        target = (
            dataframe.loc[dataframe['金额'].idxmax()]
            if extreme_type == 'max'
            else dataframe.loc[dataframe['金额'].idxmin()]
        )
        fig.add_annotation(
            x=target['Day'] - 1,
            y=target['Month'],
            text=f"{label}：{target['金额']:,.2f}元",
            showarrow=True,
            arrowhead=2,
        )

    return fig


if __name__ == "__main__":
    # 获取项目根目录（兼容打包和开发环境）
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_file = os.path.join(project_root, "zfb1.csv")
    output_dir = os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)

    df = load_data(input_file)
    fig = create_calendar_plot(df)

    output_path = os.path.join(output_dir, '日历图.html')
    static_js = os.path.join(project_root, 'cheng_xu', 'static', 'plotly-3.0.1.min.js')
    plot(fig, filename=output_path, include_plotlyjs=static_js)
    print(f"日历图已生成: {output_path}")

    fig.show()


# Section 尾注 开源许可证

# Bill_Analyzer © 2025 by ee19971 is licensed under Creative Commons Attribution 4.0 International
# https://creativecommons.org/licenses/by/4.0/
