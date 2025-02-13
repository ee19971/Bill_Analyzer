# Section 导入模块
import pandas as pd
import os
import numpy as np

# Section 获取当前工作目录
current_directory = os.getcwd()
# !!!自己填csv名字
file_path = os.path.join(current_directory, 'zfb2.csv')

# Section 导入账单
zfb = pd.read_csv(file_path, encoding='gb2312', skiprows=4)
# Section 数据清洗
# 将日期列转换为date格式
zfb['发生时间'] = pd.to_datetime(zfb['发生时间'], errors='coerce')
zfb = zfb.dropna(subset=['发生时间'])
# 将Pandas DataFrame中的列转换为NumPy数组
expenses = zfb['支出金额（-元）'].to_numpy()
incomes = zfb['收入金额（+元）'].to_numpy()
transaction_dates = zfb['发生时间'].to_numpy()

# zfb = zfb.drop(columns=['账务流水号','业务流水号','商户订单号', '商品名称'])
# 按'发生时间1'升序排列
zfb['发生时间1'] = zfb['发生时间'].dt.strftime('%H:%M:%S')
zfb = zfb.sort_values(by='发生时间1')

# print(zfb)

# 提取时间信息
year = zfb['发生时间'].dt.year.iloc[0]  # 提取年份
month = zfb['发生时间'].dt.month  # 提取月份
day = zfb['发生时间'].dt.day  # 提取日期
hour = zfb['发生时间'].dt.hour  # 提取小时
minute = zfb['发生时间'].dt.minute  # 提取分钟
second = zfb['发生时间'].dt.second  # 提取秒

# 定义变量
nan = "___"
max_expense = zfb['支出金额（-元）'].min()  # 最大支出
min_expense = zfb['支出金额（-元）'].max()  # 最小支出
min_income = zfb['收入金额（+元）'].min()  # 最小收入
max_income = zfb['收入金额（+元）'].max()  # 最大收入
total_income_year = np.sum(incomes)  # 计算年收入
average_income_month = np.divide(total_income_year, 12)  # 计算月平均收入
total_expense_year = np.sum(expenses)  # 计算年支出
average_expense_month = np.divide(total_expense_year, 12)  # 计算月平均支

earliest_transaction_date = zfb['发生时间1'].min()  # 计算最早的一笔交易时间
earliest_row = zfb.loc[zfb['发生时间1'] == earliest_transaction_date]
earliest_transaction_date = zfb['发生时间'][earliest_row.index].iloc[0]  # 最早的一笔交易时间

earliest = earliest_row['支出金额（-元）'].iloc[0] \
    if earliest_row['收入金额（+元）'].iloc[0] == 0.00 \
    else earliest_row['收入金额（+元）'].iloc[0]  # 最早的一笔交易内容
transaction_type_1 = '支出' if earliest < 0 else '收入'

latest_transaction_date = zfb['发生时间1'].max()  # 计算最晚的一笔交易时间
latest_row = zfb.loc[zfb['发生时间1'] == latest_transaction_date]
latest_transaction_date = zfb['发生时间'][latest_row.index].iloc[0]  # 最晚的一笔交易时间

latest = latest_row['支出金额（-元）'].iloc[0] \
    if latest_row['收入金额（+元）'].iloc[0] == 0.00 \
    else latest_row['收入金额（+元）'].iloc[0]  # 最晚的一笔交易内容
transaction_type_2 = '支出' if latest < 0 else '收入'

min_expense_month = zfb.loc[zfb['支出金额（-元）'] == min_expense, '发生时间'].dt.month.iloc[0]  # 最小支出的月份
max_expense_month = zfb.loc[zfb['支出金额（-元）'] == max_expense, '发生时间'].dt.month.iloc[0]  # 最大支出的月份
min_income_month = zfb.loc[zfb['收入金额（+元）'] == min_income, '发生时间'].dt.month.iloc[0]  # 最小收入的月份
max_income_month = zfb.loc[zfb['收入金额（+元）'] == max_income, '发生时间'].dt.month.iloc[0]  # 最大收入的月份
max_expense_time = zfb.loc[zfb['支出金额（-元）'] == max_expense, '发生时间'].iloc[0]  # 最大支出的时间
max_income_time = zfb.loc[zfb['收入金额（+元）'] == max_income, '发生时间'].iloc[0]  # 最大收入的时间

min_mode = zfb['支出金额（-元）'].mode()
# print(min_mode)

# 使用 value_counts() 方法查看每个值的出现次数
value_counts = zfb['支出金额（-元）'].value_counts()
# print(value_counts[min_mode])

# Section 总结
print(f"{year}年你一共花了{total_expense_year:.2f}元，平均每月花费{average_expense_month:.2f}元\r\n"
      f"{max_expense_month}月花的最多花了{max_expense}元 {min_expense_month}月花的最少花了{min_expense}元\r\n"
      f"你在{year}年一共收入{total_income_year}元，平均每月收入{average_income_month:.2f}元\r\n"
      f"{max_income_month}月的收入最多收入了{max_income}元 {min_income_month}月的收入最少是{min_income}元\r\n"
      f"最早的一笔交易是在{earliest_transaction_date}的一天的时间你{transaction_type_1}了{earliest}元\r\n"
      f"最晚的一笔交易是在{latest_transaction_date}的一天的时间你{transaction_type_2}了{latest}元\r\n"
      f"花费最多是在{max_expense_time}因为{nan}花了{max_expense}元\r\n"
      f"最高的收入是在{max_income_time}因为{nan}收入了{max_income}元\r\n")

# Section 尾注 开源许可证

# Bill_Analyzer © 2025 by ee19971 is licensed under Creative Commons Attribution 4.0 International
# https://creativecommons.org/licenses/by/4.0/
