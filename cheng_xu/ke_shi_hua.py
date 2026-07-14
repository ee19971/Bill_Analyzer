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
支持支付宝网页/APP导出和微信导出的账单格式。
"""
import os
import re
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from scipy.sparse import csr_matrix
from plotly.offline import plot

from .gong_yong_han_shu import find_csv_header_offset


# 月份中文映射常量
MONTH_NAMES = {
    1: "一月份", 2: "二月份", 3: "三月份", 4: "四月份",
    5: "五月份", 6: "六月份", 7: "七月份", 8: "八月份",
    9: "九月份", 10: "十月份", 11: "十一月份", 12: "十二月份",
}
MONTH_ORDER = list(MONTH_NAMES.values())

CHART_TYPES = {
    "日历热力图": "heatmap",
    "每日收支趋势图": "daily_trend",
    "月度收支对比图": "monthly_bar",
    "月度净收支趋势图": "monthly_net",
    "支出分类饼图": "category_pie",
}

def _clean_amount(raw_value):
    """清洗金额字符串，移除非数字字符

    Args:
        raw_value: 原始金额数据

    Returns:
        float: 清洗后的金额数值
    """
    try:
        cleaned = re.sub(r'[^\d\.-]', '', str(raw_value))
        return float(cleaned) if cleaned and cleaned != "." else 0.0
    except (ValueError, TypeError):
        return 0.0


def _detect_source(columns) -> str:
    """根据列名自动检测账单来源

    Args:
        columns: DataFrame 的列名列表

    Returns:
        str: 'alipay_web' / 'alipay_app' / 'wechat' / 'unknown'
    """
    col_set = set(columns)
    if '收入金额（+元）' in col_set and '支出金额（-元）' in col_set:
        return 'alipay_web'
    if '收/支' in col_set:
        if '金额(元)' in col_set:
            return 'wechat'
        if '金额' in col_set:
            return 'alipay_app'
    return 'unknown'


def load_data(filepath: str) -> pd.DataFrame:
    """多格式账单数据加载函数

    自动识别支付宝网页、支付宝APP、微信三种账单格式，
    支持 CSV 和 Excel（.xlsx/.xls）文件，统一归化为标准列名。

    Args:
        filepath: 账单文件路径（CSV 或 Excel）

    Returns:
        pd.DataFrame: 包含 Year/Month/Day/金额 等标准字段的 DataFrame

    Raises:
        ValueError: 文件格式不支持或列名无法识别
    """
    ext = os.path.splitext(filepath)[1].lower()

    # ---------- 1. 按文件格式读取原始数据 ----------
    if ext == '.csv':
        for enc in ('GB18030', 'utf-8', 'utf-8-sig'):
            try:
                skip_rows = find_csv_header_offset(filepath, enc)
                df = pd.read_csv(filepath, encoding=enc, skiprows=skip_rows,
                                 comment='#', dtype=str)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        else:
            raise ValueError("无法识别文件编码，请检查文件")
    elif ext in ('.xlsx', '.xls'):
        skip_rows = find_csv_header_offset(filepath, 'utf-8')
        df = pd.read_excel(filepath, skiprows=skip_rows)
    else:
        raise ValueError(f"不支持的文件格式: {ext}，仅支持 CSV 和 Excel")

    # ---------- 2. 检测来源并归一化列名 ----------
    source = _detect_source(df.columns)

    if source == 'alipay_web':
        pass
    elif source in ('alipay_app', 'wechat'):
        rename_map = {'交易时间': '发生时间'}
        if source == 'wechat':
            rename_map.update({'金额(元)': '金额', '商品': '备注'})
        else:
            rename_map.update({'商品说明': '备注'})
        df.rename(columns=rename_map, inplace=True)
    else:
        raise ValueError("无法识别账单格式，请检查列名是否包含所需字段")

    # ---------- 3. 收/支 单列格式拆分为收入/支出双列 ----------
    if '收/支' in df.columns:
        df['金额'] = df['金额'].apply(_clean_amount)
        df['收入金额（+元）'] = 0.0
        df['支出金额（-元）'] = 0.0
        income_mask = df['收/支'] == '收入'
        expense_mask = df['收/支'] == '支出'
        df.loc[income_mask, '收入金额（+元）'] = df.loc[income_mask, '金额']
        df.loc[expense_mask, '支出金额（-元）'] = -df.loc[expense_mask, '金额']

    df['收入金额（+元）'] = pd.to_numeric(df['收入金额（+元）'], errors='coerce').fillna(0.0)
    df['支出金额（-元）'] = pd.to_numeric(df['支出金额（-元）'], errors='coerce').fillna(0.0)

    # ---------- 4. 时间处理 ----------
    df['发生时间'] = pd.to_datetime(df['发生时间'], errors='coerce')
    df.dropna(subset=['发生时间'], inplace=True)

    df["Year"] = df["发生时间"].dt.year
    df["Month"] = df["发生时间"].dt.month.map(MONTH_NAMES).astype('category')
    df["Day"] = df["发生时间"].dt.day.astype('int8')

    # ---------- 5. 计算净金额 ----------
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


def _detect_account_title(dataframe: pd.DataFrame) -> str:
    """根据数据来源检测图表标题中的账户名称

    Args:
        dataframe: 已加载的账单 DataFrame（需包含原始列名信息）

    Returns:
        str: 账户名称，如"支付宝"或"微信"
    """
    if '交易单号' in dataframe.columns or '商户单号' in dataframe.columns:
        return "微信"
    if '账务流水号' in dataframe.columns or '业务流水号' in dataframe.columns:
        return "支付宝"
    if '交易订单号' in dataframe.columns:
        return "支付宝"
    return "账户"


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
    account_name = _detect_account_title(dataframe)

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
        title=f"{year}年{account_name}账户余额日历图",
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


def create_daily_trend(dataframe: pd.DataFrame) -> go.Figure:
    """生成每日收支趋势折线图

    Args:
        dataframe: 包含 发生时间/金额/Year 字段的DataFrame

    Returns:
        go.Figure: Plotly折线图对象
    """
    year = dataframe['Year'].iloc[0]
    account_name = _detect_account_title(dataframe)

    daily = dataframe.groupby(dataframe['发生时间'].dt.date).agg(
        收入=('收入金额（+元）', 'sum'),
        支出=('支出金额（-元）', 'sum'),
    ).reset_index()
    daily.rename(columns={'发生时间': '日期'}, inplace=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily['日期'], y=daily['收入'],
        name='收入', mode='lines+markers',
        line=dict(color='#2ecc71', width=2),
        marker=dict(size=5),
    ))
    fig.add_trace(go.Scatter(
        x=daily['日期'], y=daily['支出'],
        name='支出', mode='lines+markers',
        line=dict(color='#e74c3c', width=2),
        marker=dict(size=5),
    ))

    fig.update_layout(
        title=f"{year}年{account_name}每日收支趋势",
        xaxis_title="日期",
        yaxis_title="金额（元）",
        height=600, width=1200,
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
    )
    return fig


def create_monthly_bar(dataframe: pd.DataFrame) -> go.Figure:
    """生成月度收支对比柱状图

    Args:
        dataframe: 包含 Month/Year/金额 字段的DataFrame

    Returns:
        go.Figure: Plotly柱状图对象
    """
    year = dataframe['Year'].iloc[0]
    account_name = _detect_account_title(dataframe)

    monthly = dataframe.groupby(
        dataframe['Month'], observed=False
    ).agg(
        收入=('收入金额（+元）', 'sum'),
        支出=('支出金额（-元）', 'sum'),
    ).reindex(MONTH_ORDER, fill_value=0.0)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly.index, y=monthly['收入'],
        name='收入', marker_color='#2ecc71',
    ))
    fig.add_trace(go.Bar(
        x=monthly.index, y=monthly['支出'],
        name='支出', marker_color='#e74c3c',
    ))

    fig.update_layout(
        title=f"{year}年{account_name}月度收支对比",
        xaxis_title="月份",
        yaxis_title="金额（元）",
        barmode='group',
        height=600, width=1200,
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
    )
    return fig


def create_monthly_net(dataframe: pd.DataFrame) -> go.Figure:
    """生成月度净收支趋势折线图

    Args:
        dataframe: 包含 Month/Year/金额 字段的DataFrame

    Returns:
        go.Figure: Plotly折线图对象
    """
    year = dataframe['Year'].iloc[0]
    account_name = _detect_account_title(dataframe)

    monthly = dataframe.groupby(
        dataframe['Month'], observed=False
    ).agg(
        净额=('金额', 'sum'),
    ).reindex(MONTH_ORDER, fill_value=0.0)

    colors = ['#2ecc71' if v >= 0 else '#e74c3c' for v in monthly['净额']]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly.index, y=monthly['净额'],
        mode='lines+markers+text',
        name='净收支',
        line=dict(color='#3498db', width=3),
        marker=dict(size=10, color=colors),
        text=[f"{v:,.2f}" for v in monthly['净额']],
        textposition='top center',
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="gray")

    fig.update_layout(
        title=f"{year}年{account_name}月度净收支趋势",
        xaxis_title="月份",
        yaxis_title="净金额（元）",
        height=600, width=1200,
    )
    return fig


def create_category_pie(dataframe: pd.DataFrame) -> go.Figure:
    """生成支出分类饼图

    Args:
        dataframe: 包含 备注/金额 字段的DataFrame

    Returns:
        go.Figure: Plotly饼图对象
    """
    year = dataframe['Year'].iloc[0]
    account_name = _detect_account_title(dataframe)

    expenses = dataframe[dataframe['支出金额（-元）'] < 0].copy()
    if expenses.empty:
        fig = go.Figure()
        fig.update_layout(title=f"{year}年{account_name}支出分类（无支出数据）")
        return fig

    category_col = '备注' if '备注' in expenses.columns else '业务类型'
    if category_col not in expenses.columns:
        category_col = dataframe.columns[3]

    expenses['金额绝对值'] = expenses['支出金额（-元）'].abs()

    cat_grouped = expenses.groupby(category_col, observed=False)['金额绝对값'].sum()
    cat_grouped = cat_grouped[cat_grouped > 0].sort_values(ascending=False)

    if len(cat_grouped) > 10:
        top = cat_grouped.iloc[:10]
        other_sum = cat_grouped.iloc[10:].sum()
        cat_grouped = pd.concat([top, pd.Series({'其他': other_sum})])

    cat_grouped.index = [str(idx) if pd.notna(idx) and str(idx).strip() else '未分类'
                         for idx in cat_grouped.index]

    fig = go.Figure(go.Pie(
        labels=cat_grouped.index,
        values=cat_grouped.values,
        hole=0.3,
        textinfo='label+percent',
        hovertemplate='%{label}<br>金额: %{value:,.2f}元<br>占比: %{percent}<extra></extra>',
    ))

    fig.update_layout(
        title=f"{year}年{account_name}支出分类",
        height=600, width=900,
        legend=dict(orientation='h', yanchor='bottom', y=-0.2),
    )
    return fig


def generate_chart_html(csv_path: str, output_dir: str,
                        chart_type: str = "heatmap") -> str:
    """从账单文件生成指定类型的图表HTML

    支持 CSV 和 Excel 格式，兼容支付宝网页/APP及微信账单。

    Args:
        csv_path: 账单文件路径（CSV 或 Excel）
        output_dir: HTML输出目录
        chart_type: 图表类型标识（heatmap/daily_trend/monthly_bar/monthly_net/category_pie）

    Returns:
        str: 生成的HTML文件完整路径
    """
    chart_creators = {
        "heatmap": (create_calendar_plot, "日历热力图"),
        "daily_trend": (create_daily_trend, "每日收支趋势图"),
        "monthly_bar": (create_monthly_bar, "月度收支对比图"),
        "monthly_net": (create_monthly_net, "月度净收支趋势图"),
        "category_pie": (create_category_pie, "支出分类饼图"),
    }

    creator_func, chart_label = chart_creators.get(
        chart_type, (create_calendar_plot, "日历热力图")
    )

    df = load_data(csv_path)
    fig = creator_func(df)

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'消费分析-{chart_label}.html')
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_js = os.path.join(project_root, 'cheng_xu', 'static', 'plotly-3.7.0.min.js')
    plot(fig, filename=output_path, include_plotlyjs=static_js,
         config={'locale': 'zh-CN'})

    with open(output_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    html_content = html_content.replace('<html>', '<html lang="zh-CN">', 1)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return output_path


def generate_calendar_html(csv_path: str, output_dir: str) -> str:
    """从账单文件生成日历热力图HTML（向后兼容）

    Args:
        csv_path: 账单文件路径（CSV 或 Excel）
        output_dir: HTML输出目录

    Returns:
        str: 生成的HTML文件完整路径
    """
    return generate_chart_html(csv_path, output_dir, "heatmap")


if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_file = os.path.join(project_root, "zfb1.csv")
    output_dir = os.path.join(project_root, "output")

    result_path = generate_chart_html(input_file, output_dir, "heatmap")
    print(f"日历图已生成: {result_path}")

# Section 尾注 开源许可证

# Bill_Analyzer © 2025 by ee19971 is licensed under Creative Commons Attribution 4.0 International
# https://creativecommons.org/licenses/by/4.0/
