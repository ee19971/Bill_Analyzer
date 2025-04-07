#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------

# @文件：ke_shi_hua.py
# @时间：2025年04月06日08:57
# @作者：ee19971
# @邮箱：3504275453@qq.com
# @作用：Bill_Analyzer项目-账单可视化分析模块

# ------------------------------------------------------------------------------
import plotly.graph_objects as go
import pandas as pd

# 读取CSV文件（示例路径）
df = pd.read_csv(r"C:\test\Bill_Analyzer\zfb1.csv",
                 encoding="GB18030",
                 header=0,
                 )

# 时间处理
df["发生时间"] = pd.to_datetime(df["发生时间"], format='%Y/%m/%d %H:%M')
df["Year"] = df["发生时间"].dt.year
df["Month"] = df["发生时间"].dt.month.map({
    1: "一月份", 2: "二月份", 3: "三月份", 4: "四月份",
    5: "五月份", 6: "六月份", 7: "七月份", 8: "八月份",
    9: "九月份", 10: "十月份", 11: "十一月份", 12: "十二月份"
})
df["Day"] = df["发生时间"].dt.day
df["金额"] = df["收入金额（+元）"] + df["支出金额（-元）"]
max_value = df["金额"].max()
min_value = df["金额"].min()


# 创建日历图函数
def create_calendar_plot(dataframe):
    # 定义完整日期范围
    month_order = ["一月份", "二月份", "三月份", "四月份", "五月份", "六月份",
                   "七月份", "八月份", "九月份", "十月份", "十一月份", "十二月份"]
    day_order = list(range(1, 32))

    # 生成数据透视表
    pivot_df = dataframe.pivot_table(
        index="Month",
        columns="Day",
        values="金额",
        aggfunc="sum",
        fill_value=0
    )

    # 补全所有可能日期
    pivot_df = pivot_df.reindex(
        index=month_order,
        columns=day_order,
        fill_value=0
    )

    # 生成悬停文本
    hover_text = []
    for month in month_order:
        month_text = []
        for day in day_order:
            value = pivot_df.loc[month, day]

            # 添加完整的类型判断逻辑
            if value > 0:
                trans_type = "收入"
            elif value < 0:
                trans_type = "支出"
            else:
                trans_type = "无交易"

            month_text.append(
                f"日期：{day}号<br>"
                f"月份：{month}<br>"
                f"类型：{trans_type}<br>"
                f"金额：{value:,.2f}元"
            )
        hover_text.append(month_text)

    # 创建热力图
    fig = go.Figure(go.Heatmap(
        z=pivot_df.values,
        x=[str(d) for d in day_order],
        y=month_order,
        colorscale="Viridis",
        hoverinfo="text",
        text=hover_text,
        textfont={"size": 10},
        zsmooth=False,
        zmin=min_value + 0.5,  # 设置最小值
        zmax=max_value,  # 设置最大值
        zmid=0  # 设置颜色中心点为0值
    ))

    # 优化布局
    fig.update_layout(
        updatemenus=[
            dict(
                type="dropdown",
                buttons=[
                    dict(label="2025年",
                         method="update",
                         args=[{"visible": [True]},
                               {"title": "2025年支付宝账户余额日历图"}]),
                    dict(label="2024年",
                         method="update",
                         args=[{"visible": [False]},
                               {"title": "2024年支付宝账户余额日历图"}])
                ],
                x=1,
                y=1.15
            )
        ],
        modebar_add=[
            'zoom2d',
            'pan2d',
            'zoomIn2d',
            'zoomOut2d',
            'autoScale2d',
            'resetScale2d'
        ],
        title=f"{dataframe['Year'].iloc[0]}年支付宝账户余额日历图",
        xaxis_title="日期",
        yaxis_title="月份",
        height=800,
        width=1200,
        dragmode='pan',  # 启用平移模式
        xaxis=dict(
            ticktext=day_order[::3],
            tickangle=45,
            fixedrange=False,  # 允许x轴缩放
            rangeslider=dict(visible=True),  # 显示范围滑动条
            range=[0.5, 31.5]  # 限制日期显示范围
        ),
        yaxis=dict(
            tickmode="array",
            tickvals=month_order,
            fixedrange=False,  # 允许y轴缩放
            autorange=False,  # 禁用自动调整范围
            range=[-0.5, 11.5]  # 对应12个月份的索引范围
        ),
        coloraxis_colorbar=dict(
            title="净收支（元）",
            tickprefix="¥",
            ticksuffix="元",
            tickformat=",.0f",
            thickness=25,
            lenmode="pixels",
            len=300
        ),
    )
    # 标记最大值
    max_day = df.loc[df['金额'].idxmax()]
    fig.add_annotation(
        x=max_day['Day'] - 1,
        y=max_day['Month'],
        text=f"最大收入：{max_day['金额']:,.2f}元",
        showarrow=True,
        arrowhead=2
    )
    # 标记最小值
    min_day = df.loc[df['金额'].idxmin()]
    fig.add_annotation(
        x=min_day['Day'] - 1,
        y=min_day['Month'],
        text=f"最大支出：{min_day['金额']:,.2f}元",
        showarrow=True,
        arrowside="end",
        arrowhead=2
    )
    return fig


# 生成图表
fig = create_calendar_plot(df)
fig.show()
