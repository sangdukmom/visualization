import altair as alt
import pandas as pd
import numpy as np

import datetime

import re

alt.data_transformers.enable("vegafusion")

fab_data = pd.read_csv('C:/Users/SKSiltron/Desktop/project/signpost_project/1_data/visual_customer/Fab_Capa_300mm.csv')
usage_data = pd.read_csv('C:/Users/SKSiltron/Desktop/project/signpost_project/1_data/visual_customer/2018년01월~24년12월_300mm CustomerUsageList_20250305_Sheet1.csv', header=[0,1])


### 1-2. usage data columns 정리
### - 멀티컬럼 생성 후 df 적용
new_cols = []

for col in usage_data.columns:
    #print(col)

    if 'Unnamed' not in col[0]:
        prev_col = ''.join(re.findall(r'\d+', col[0]))
        # print prev_col
        # print(col[0])
    
    if 'Unnamed' in col[1]:
        new_cols.append(col[0])
    
    else:
        new_cols.append(prev_col + '-' + col[1])

usage_data.columns = new_cols
usage_data.rename(columns={'Site Name(참고용)': 'Site Name'}, inplace=True)
usage_data = usage_data[usage_data['Supplier']!='Subtotal']

usage_data.to_csv('C:/Users/SKSiltron/Desktop/project/signpost_project/1_data/visual_customer/usage_data.csv')

# --- 1. 전처리: Wide -> Long 변환 ---

# (0) Usage[2024] 컬럼 drop
usage_data = usage_data.drop(columns=['Usage [2024]'])

# (1) usage_data 전처리
# id_vars: 고정 컬럼 (첫 15개 컬럼)
id_vars_usage = ['Size', 'Site Name', '구분', 'Team', 'Customer', 'Country', '사업', 'IDM/Foundry', 'Device', 'Grade', 'Grade1', 'Grade2', '본사', 'Supplier']

# time_vars: 나머지 컬럼(월 별 시간 정보)
time_vars_usage = [col for col in usage_data.columns if col not in id_vars_usage]

# melt 로 long format 으로 변환
usage_long = usage_data.melt(id_vars=id_vars_usage, value_vars=time_vars_usage,var_name='Date', value_name='Usage')

# Date 컬럼을 datetime 으로 변환 (예: '2018-01' -> Timestamp)
usage_long['Date'] = pd.to_datetime(usage_long['Date'], format='%Y-%m')

# (2) fab_data 전처리
# id_vars: 고정 컬럼 (첫 18개 컬럼)

id_vars_fab = ['구분', 'Customer', 'Customer2', 'Location', 'Fab',
               'IDM/Foundry', 'Country', 'Region', 'Origin', 'D/R',
               'Device1', 'Device2', 'Device3', 'Grade', 'Grade1',
               'Grade2', 'Team', '사업']


# time_vars : 나머지 컬럼 (분기 별 시간 정보)
time_vars_fab = [col for col in fab_data.columns if col not in id_vars_fab]
fab_long = fab_data.melt(id_vars=id_vars_fab, value_vars=time_vars_fab, var_name='Quarter', value_name='Fab_Capa')

# fab_data 의 분기 문자열("22.2Q" 등)을 datetime 으로 변환하는 함수
def quarter_to_date(q):
    m = re.match(r"(\d{2})\.(\d)Q", q)
    if m:
        yy = int(m.group(1))
        qtr = int(m.group(2))
        year = 2000 + yy # 예: 22 -> 2022
        # 분기별 시작월 : Q1:1, Q2:4, Q3:7, Q4:10
        month = {1: 1, 2: 4, 3: 7, 4: 10}[qtr]
        return pd.Timestamp(year=year, month=month, day=1)
    return pd.NaT

fab_long['Date'] = fab_long['Quarter'].apply(quarter_to_date)

# fab_data에는 Device 관련 컬럼이 없으므로, Device1/2/3 중 첫 번째 값(non-null)을 선택하여 "Device" 컬럼 생성
fab_long['Device'] = fab_long[['Device1', 'Device2', 'Device3']].bfill(axis=1).iloc[:, 0]

# --- 2. 필터링을 위한 선택(Selection) 생성 ---

# 양쪽 데이터셋에 적요할 필터 : Customer, Device, Country, Device 상세 (Grade)
# usage_data 에만 존재하는 필터: Wafer (Size)

# 각 필터의 옵션을 양쪽 DataFrame 에서 union 하여 결정
customer_options = sorted(list(set(usage_long['Customer'].dropna().unique()).union(
                               set(fab_long['Customer'].dropna().unique()))))
device_options = sorted(list(set(usage_long['Device'].dropna().unique()).union(
                             set(fab_long['Device'].dropna().unique()))))
wafer_options = sorted(list(usage_long['Size'].dropna().unique()))
country_options = sorted(list(set(usage_long['Country'].dropna().unique()).union(
                              set(fab_long['Country'].dropna().unique()))))
device_detail_options = sorted(list(set(usage_long['Grade'].dropna().unique()).union(
                                    set(fab_long['Grade'].dropna().unique()))))


# selection bindings 생성
customer_sel = alt.selection_single(
    fields=['Customer'],
    bind=alt.binding_select(options=customer_options, name='Customer'),
    # init={'Customer': customer_options[0]}
)

device_sel = alt.selection_single(
    fields=['Device'],
    bind=alt.binding_select(options=device_options, name='Device'),
    # init={'Device': device_options[0]}
)

wafer_sel = alt.selection_single(
    fields=['Size'],
    bind=alt.binding_select(options=wafer_options, name='Wafer'),
    # init={'Size': wafer_options[0]}
)

country_sel = alt.selection_single(
    fields=['Country'],
    bind=alt.binding_select(options=country_options, name='Country'),
    # init={'Country': country_options[0]}
)

device_detail_sel = alt.selection_single(
    fields=['Grade'],
    bind=alt.binding_select(options=device_options, name='Device 상세'),
    # init = {'Grade': device_detail_oprions[0]}
)

# --- 3. Altair 차트 생성 ---
# (1) usage_data 차트 (월별 가동률)
usage_chart = alt.Chart(usage_long).mark_line().encode(
    x=alt.X('Date:T', title='Date'),
    y=alt.Y('Usage:Q', title='Usage'),
    color=alt.Color('Customer:N', legend=alt.Legend(title='Customer')),
    tooltip=['Customer', 'Device', 'Size', 'Country', 'Grade', 'Date:T', 'Usage:Q']
).add_selection(
    customer_sel, device_sel, wafer_sel, country_sel, device_detail_sel
).transform_filter(
    customer_sel
).transform_filter(
    device_sel
).transform_filter(
    wafer_sel
).transform_filter(
    country_sel
).transform_filter(
    device_detail_sel
)

# (2) fab_data 차트 (분기별 fab_capacity)
fab_chart = alt.Chart(fab_long).mark_line().encode(
    x=alt.X('Date:T', title='Date'),
    y=alt.Y('Fab_Capa:Q', title='Fab Capacity'),
    color=alt.Color('Customer:N', legend=alt.Legend(title='Customer')),
    tooltip=['Customer', 'Device', 'Country', 'Grade', 'Quarter', 'Fab_Capa']
).add_selection(
    customer_sel, device_sel, country_sel, device_detail_sel
).transform_filter(
    customer_sel
).transform_filter(
    device_sel # fab_long now has "Device" 컬럼
).transform_filter(
    country_sel
).transform_filter(
    device_detail_sel
)

# fab_chart 에는 Wafer(=Size) 정보가 없으므로 wafer sel 은 적용하지 않음

# (3) 두 차트를 수직으로 결헙(상호 필터링 적용)
combined_chart = alt.vconcat(
    usage_chart.properties(title='Usage Trend'),
    fab_chart.properties(title='Fab Capacity Trend')
).resolve_scale(
    color='independent'
)

combined_chart
