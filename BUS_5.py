# MY_SERVICE_KEY = "6fc222f7a07ce61876bf07b46533721a192b38b26b2ff8aff34d8bdc837f5ba1" 

import streamlit as st
import requests
import holidays
from datetime import datetime, timedelta

# ---------------------------------------------------------
# [필수] 본인의 공공데이터포털 인증키를 입력하세요
MY_SERVICE_KEY = "6fc222f7a07ce61876bf07b46533721a192b38b26b2ff8aff34d8bdc837f5ba1" 
# ---------------------------------------------------------

st.set_page_config(page_title="동구5 & 지하철 안내판", page_icon="🚌")

# 한국 시간 및 공휴일 판별 함수
def get_now_info():
    now = datetime.utcnow() + timedelta(hours=9)
    kr_holidays = holidays.KR() # 한국 공휴일 정보
    
    # 주말(토:5, 일:6)이거나 공휴일인 경우 True
    is_holiday_mode = now.weekday() >= 5 or now in kr_holidays
    return now, is_holiday_mode

def get_bus_data(bsId):
    url = f"http://apis.data.go.kr/6270000/dbmsapi02/getRealtime02?serviceKey={MY_SERVICE_KEY}&bsId={bsId}&_type=json"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json().get('body', {}).get('items', [])
        return []
    except: return []

# 실제 지하철 시간표 데이터 (평일/주말·공휴일 구분)
def get_real_subway_schedule(station_type):
    now, is_holiday_mode = get_now_info()
    now_str = now.strftime("%H:%M")

    # 1. 반야월역 (상행/설화명곡 방면)
    ban_weekday = ["05:39", "05:51", "06:02", "06:13", "06:23", "06:33", "06:42", "06:51", "07:00", "07:08", "07:16", "07:24", "07:32", "07:40", "07:48", "07:56", "08:04", "08:12", "08:21", "08:31", "08:41", "08:51", "09:01", "09:12", "09:24", "09:36", "09:48", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"]
    ban_holiday = ["05:39", "05:54", "06:09", "06:24", "06:39", "06:54", "07:09", "07:24", "07:39", "07:54", "08:09", "08:24", "08:39", "08:54", "09:09", "09:24", "09:39", "09:54", "10:09", "11:09", "12:09", "13:09", "14:09", "15:09", "16:09", "17:09"]

    # 2. 동대구역 (하행/안심 방면)
    dong_weekday = ["06:05", "06:17", "06:28", "06:39", "06:49", "06:59", "07:08", "07:17", "07:26", "07:34", "07:42", "07:50", "07:58", "08:06", "08:14", "08:22", "08:30", "08:38", "08:47", "08:57", "09:07", "09:17", "09:27", "09:38", "10:02", "11:02", "12:02", "13:02", "14:02", "15:02", "16:02", "17:02"]
    dong_holiday = ["06:05", "06:20", "06:35", "06:50", "07:05", "07:20", "07:35", "07:50", "08:05", "08:20", "08:35", "08:50", "09:05", "09:20", "09:35", "09:50", "10:05", "11:05", "12:05", "13:05", "14:05", "15:05", "16:05", "17:05"]

    if station_type == "ban":
        target_list = ban_holiday if is_holiday_mode else ban_weekday
    else:
        target_list = dong_holiday if is_holiday_mode else dong_weekday
    
    upcoming = [t for t in target_list if t >= now_str]
    mode_name = "주말/공휴일" if is_holiday_mode else "평일"
    return upcoming[:5], mode_name

# --- UI 구성 ---
now_k, is_h = get_now_info()
st.title("🚌 통합 교통 안내판")
st.subheader(f"🇰🇷 현재 시각: {now_k.strftime('%Y-%m-%d %H:%M:%S')}")

# [버스 섹션]
st.header("🚏 실시간 버스 (동구5)")
bus_stations = [{'name': '📍 율하고가교1', 'id': '7011061400'}, {'name': '📍 항공교통본부앞', 'id': '7011060900'}]

for bs in bus_stations:
    with st.expander(bs['name'], expanded=True):
        data = get_bus_data(bs['id'])
        found = False
        if data:
            for item in data:
                if '동구5' in str(item.get('routeNo', '')):
                    for bus in item.get('arrList', []):
                        st.metric(label="버스 도착 예정", value=bus.get('arrState'))
                        st.write(f"🚩 현재 위치: {bus.get('bsNm')}")
                        found = True
        if not found: st.info("진입 중인 동구5번 없음")

# [지하철 섹션]
st.divider()
table_ban, mode_ban = get_real_subway_schedule("ban")
table_dong, mode_dong = get_real_subway_schedule("dong")
st.header(f"🚇 지하철 시간표 ({mode_ban})")

col1, col2 = st.columns(2)
with col1:
    st.success("🚉 반야월 (상행)")
    st.caption("설화명곡 방면")
    if table_ban: st.table({"출발": table_ban})
    else: st.write("운행 종료")

with col2:
    st.success("🚉 동대구 (하행)")
    st.caption("안심 방면")
    if table_dong: st.table({"출발": table_dong})
    else: st.write("운행 종료")

if st.button('🔄 새로고침'):
    st.rerun()

