# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------

# @文件：ke_shi_hua_echarts.py
# @时间：2025年07月22日
# @作者：ee19971
# @邮箱：3504275453@qq.com
# @作用：Bill_Analyzer项目 - 账单可视化分析模块（ECharts版）

# ------------------------------------------------------------------------------
"""
账单可视化模块（ECharts版）

基于 ECharts 生成多种图表，展示收支数据分布。
复用 ke_shi_hua.py 的数据加载逻辑，提供与 Plotly 版不同的图表类型。
"""
import os
import json
from datetime import datetime

from .ke_shi_hua import load_data, get_available_years, _detect_account_title, MONTH_ORDER

ECHARTS_CHART_TYPES = {
    "收支瀑布图": "waterfall",
    "支出玫瑰图": "rose",
    "周消费分布图": "weekday",
    "年度累计支出曲线": "cumulative",
    "月度收支雷达图": "radar",
}


def _create_waterfall_chart(dataframe, year, account_name):
    """生成月度收支瀑布图配置"""
    import pandas as pd

    monthly = dataframe.groupby(
        dataframe['Month'], observed=False
    ).agg(
        收入=('收入金额（+元）', 'sum'),
        支出=('支出金额（-元）', 'sum'),
    ).reindex(MONTH_ORDER, fill_value=0.0)

    months = [m.replace('份', '') for m in MONTH_ORDER]
    income_data = [round(v, 2) for v in monthly['收入'].values]
    expense_data = [round(v, 2) for v in monthly['支出'].values]
    net_data = [round(i + e, 2) for i, e in zip(income_data, expense_data)]

    option = {
        "title": {"text": f"{year}年{account_name}月度收支瀑布图", "left": "center"},
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": "{b}<br/>{a0}: {c0}元<br/>{a1}: {c1}元<br/>{a2}: {c2}元",
        },
        "legend": {"data": ["收入", "支出", "净收支"], "top": 30},
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
        "xAxis": {"type": "category", "data": months},
        "yAxis": {"type": "value", "name": "金额（元）"},
        "series": [
            {
                "name": "收入",
                "type": "bar",
                "stack": "total",
                "itemStyle": {"color": "#2ecc71"},
                "data": income_data,
            },
            {
                "name": "支出",
                "type": "bar",
                "stack": "total",
                "itemStyle": {"color": "#e74c3c"},
                "data": expense_data,
            },
            {
                "name": "净收支",
                "type": "line",
                "symbol": "circle",
                "symbolSize": 8,
                "itemStyle": {"color": "#3498db"},
                "data": net_data,
            },
        ],
    }
    return option


def _create_rose_chart(dataframe, year, account_name):
    """生成支出分类玫瑰图配置"""
    import pandas as pd

    expenses = dataframe[dataframe['支出金额（-元）'] < 0].copy()
    if expenses.empty:
        return {"title": {"text": f"{year}年{account_name}支出分类（无支出数据）", "left": "center"}}

    category_col = '备注' if '备注' in expenses.columns else '业务类型'
    if category_col not in expenses.columns:
        category_col = dataframe.columns[3]

    expenses['金额绝对值'] = expenses['支出金额（-元）'].abs()
    cat_grouped = expenses.groupby(category_col, observed=False)['金额绝对值'].sum()
    cat_grouped = cat_grouped[cat_grouped > 0].sort_values(ascending=False)

    if len(cat_grouped) > 10:
        top = cat_grouped.iloc[:10]
        other_sum = cat_grouped.iloc[10:].sum()
        cat_grouped = pd.concat([top, pd.Series({'其他': other_sum})])

    rose_data = [
        {"name": str(idx) if pd.notna(idx) and str(idx).strip() else '未分类', "value": round(v, 2)}
        for idx, v in cat_grouped.items()
    ]

    option = {
        "title": {"text": f"{year}年{account_name}支出分类玫瑰图", "left": "center"},
        "tooltip": {"trigger": "item", "formatter": "{b}: {c}元 ({d}%)"},
        "legend": {
            "orient": "vertical",
            "left": "left",
            "top": "middle",
            "type": "scroll",
        },
        "series": [
            {
                "name": "支出分类",
                "type": "pie",
                "radius": ["15%", "70%"],
                "center": ["55%", "50%"],
                "roseType": "area",
                "itemStyle": {"borderRadius": 8},
                "data": rose_data,
            }
        ],
    }
    return option


def _create_weekday_chart(dataframe, year, account_name):
    """生成周消费分布图配置"""
    import pandas as pd

    df = dataframe.copy()
    df['星期'] = df['发生时间'].dt.dayofweek

    weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

    weekday_stats = df.groupby('星期').agg(
        支出=('支出金额（-元）', lambda x: x[x < 0].sum()),
        笔数=('支出金额（-元）', lambda x: (x < 0).sum()),
    ).reindex(range(7), fill_value=0.0)

    expense_data = [round(v, 2) for v in weekday_stats['支出'].values]
    count_data = [int(v) for v in weekday_stats['笔数'].values]
    avg_data = [round(e / c, 2) if c > 0 else 0 for e, c in zip(expense_data, count_data)]

    option = {
        "title": {"text": f"{year}年{account_name}周消费分布", "left": "center"},
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
        },
        "legend": {"data": ["支出总额", "交易笔数", "平均单笔"], "top": 30},
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
        "xAxis": {"type": "category", "data": weekday_names},
        "yAxis": [
            {"type": "value", "name": "金额（元）", "position": "left"},
            {"type": "value", "name": "笔数", "position": "right"},
        ],
        "series": [
            {
                "name": "支出总额",
                "type": "bar",
                "itemStyle": {"color": "#e74c3c"},
                "data": expense_data,
            },
            {
                "name": "交易笔数",
                "type": "bar",
                "yAxisIndex": 1,
                "itemStyle": {"color": "#f39c12"},
                "data": count_data,
            },
            {
                "name": "平均单笔",
                "type": "line",
                "symbol": "diamond",
                "symbolSize": 10,
                "itemStyle": {"color": "#9b59b6"},
                "data": avg_data,
            },
        ],
    }
    return option


def _create_cumulative_chart(dataframe, year, account_name):
    """生成年度累计支出曲线配置"""
    import pandas as pd

    df = dataframe.copy()
    expenses = df[df['支出金额（-元）'] < 0].copy()
    expenses['日期'] = expenses['发生时间'].dt.date

    daily_expense = expenses.groupby('日期')['支出金额（-元）'].sum().abs()
    daily_expense = daily_expense.sort_index()
    cumulative = daily_expense.cumsum()

    dates = [str(d) for d in cumulative.index]
    cum_values = [round(v, 2) for v in cumulative.values]
    daily_values = [round(v, 2) for v in daily_expense.values]

    option = {
        "title": {"text": f"{year}年{account_name}年度累计支出曲线", "left": "center"},
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
        },
        "legend": {"data": ["累计支出", "当日支出"], "top": 30},
        "grid": {"left": "3%", "right": "4%", "bottom": "12%", "containLabel": True},
        "dataZoom": [
            {"type": "slider", "start": 0, "end": 100, "bottom": 5},
        ],
        "xAxis": {"type": "category", "data": dates, "boundaryGap": False},
        "yAxis": {"type": "value", "name": "金额（元）"},
        "series": [
            {
                "name": "累计支出",
                "type": "line",
                "smooth": True,
                "areaStyle": {"opacity": 0.3},
                "itemStyle": {"color": "#e74c3c"},
                "data": cum_values,
            },
            {
                "name": "当日支出",
                "type": "bar",
                "itemStyle": {"color": "#f39c12", "opacity": 0.6},
                "data": daily_values,
            },
        ],
    }
    return option


def _create_radar_chart(dataframe, year, account_name):
    """生成月度收支雷达图配置"""
    import pandas as pd

    monthly = dataframe.groupby(
        dataframe['Month'], observed=False
    ).agg(
        收入=('收入金额（+元）', 'sum'),
        支出=('支出金额（-元）', lambda x: abs(x[x < 0].sum())),
    ).reindex(MONTH_ORDER, fill_value=0.0)

    income_data = [round(v, 2) for v in monthly['收入'].values]
    expense_data = [round(v, 2) for v in monthly['支出'].values]
    max_income = max(income_data) if income_data else 1
    max_expense = max(expense_data) if expense_data else 1
    max_val = max(max_income, max_expense) * 1.2

    months_short = [m.replace('份', '') for m in MONTH_ORDER]

    option = {
        "title": {"text": f"{year}年{account_name}月度收支雷达图", "left": "center"},
        "tooltip": {"trigger": "item"},
        "legend": {"data": ["收入", "支出"], "top": 30},
        "radar": {
            "indicator": [{"name": m, "max": round(max_val, 2)} for m in months_short],
            "center": ["50%", "55%"],
            "radius": "65%",
        },
        "series": [
            {
                "type": "radar",
                "data": [
                    {
                        "value": income_data,
                        "name": "收入",
                        "areaStyle": {"opacity": 0.2},
                        "lineStyle": {"color": "#2ecc71"},
                        "itemStyle": {"color": "#2ecc71"},
                    },
                    {
                        "value": expense_data,
                        "name": "支出",
                        "areaStyle": {"opacity": 0.2},
                        "lineStyle": {"color": "#e74c3c"},
                        "itemStyle": {"color": "#e74c3c"},
                    },
                ],
            }
        ],
    }
    return option


SINGLE_CREATORS = {
    "waterfall": _create_waterfall_chart,
    "rose": _create_rose_chart,
    "weekday": _create_weekday_chart,
    "cumulative": _create_cumulative_chart,
    "radar": _create_radar_chart,
}


def generate_echarts_html(csv_path: str, output_dir: str,
                          chart_type: str = "waterfall",
                          year=None) -> str:
    """从账单文件生成 ECharts 图表 HTML

    Args:
        csv_path: 账单文件路径（CSV 或 Excel）
        output_dir: HTML输出目录
        chart_type: 图表类型标识
        year: 年份筛选参数

    Returns:
        str: 生成的HTML文件完整路径
    """
    df = load_data(csv_path)
    available_years = sorted(df['Year'].unique())

    if year is None:
        year = max(available_years)
    if str(year).lower() == 'all':
        year = max(available_years)
    year = int(year)

    df_filtered = df[df['Year'] == year].copy()
    account_name = _detect_account_title(df_filtered)

    creator_func = SINGLE_CREATORS.get(chart_type, _create_waterfall_chart)
    option = creator_func(df_filtered, year, account_name)

    chart_label = {v: k for k, v in ECHARTS_CHART_TYPES.items()}.get(chart_type, "收支瀑布图")

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f'消费分析-{chart_label}-{timestamp}.html')

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    echarts_js = os.path.join(project_root, 'cheng_xu', 'static', 'echarts.min.js')
    echarts_uri = 'file:///' + echarts_js.replace('\\', '/')

    option_json = json.dumps(option, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>消费分析-{chart_label}</title>
    <script src="{echarts_uri}"></script>
    <style>
        * {{ margin: 0; padding: 0; }}
        #chart {{ width: 100%; height: 100vh; }}
    </style>
</head>
<body>
    <div id="chart"></div>
    <script>
        var chart = echarts.init(document.getElementById('chart'));
        var option = {option_json};
        chart.setOption(option);
        window.addEventListener('resize', function() {{
            chart.resize();
        }});
    </script>
</body>
</html>"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return output_path
