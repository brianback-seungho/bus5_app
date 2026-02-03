# MY_SERVICE_KEY = "6fc222f7a07ce61876bf07b46533721a192b38b26b2ff8aff34d8bdc837f5ba1" 

import streamlit as st
import requests
import holidays
from datetime import datetime, timedelta

# ---------------------------------------------------------
# [필수] 본인의 공공데이터포털 인증키를 입력하세요
MY_SERVICE_KEY = "사용자님의_인증키_입력" 
# ---------------------------------------------------------

st.set_page_config(page_title="동구5 & 지하철 안내판", page_icon="🚌")

def get_now_info():
    now = datetime.utcnow() + timedelta(hours=9)
    kr_holidays = holidays.KR()
    # 주말(토/일)이거나 공휴일인 경우 True
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

# 대구 1호선 운행 패턴에 따른 시간표 자동 생성 함수
def get_optimized_schedule(station_type):
    now, is_holiday_mode = get_now_info()
    now_str = now.strftime("%H:%M")
    
    # 배차 간격 설정 (분 단위)
    if is_holiday_mode:
        interval = 13 # 주말/공휴일 약 13분 간격
    else:
        # 평일 출퇴근 시간대(07~09, 18~20)는 8분, 나머지는 10분
        curr_hour = now.hour
        interval = 8 if (7 <= curr_hour <= 9 or 18 <= curr_hour <= 20) else 10

    # 역별 첫차 시간 기준 설정
    # 반야월(상행) 첫차 약 05:39 / 동대구(하행) 첫차 약 06:05
    start_time = datetime.strptime("05:39" if station_type == "ban" else "06:05", "%H:%M")
    end_time = datetime.strptime("23:30", "%H:%M")
    
    schedule = []
    current = start_time
    while current <= end_time:
        schedule.append(current.strftime("%H:%M"))
        current += timedelta(minutes=interval)
    
    # 현재 시간 이후의 열차 5개 추출
    upcoming = [t for t in schedule if t >= now_str]
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
table_ban, mode_ban = get_optimized_schedule("ban")
table_dong, mode_dong = get_optimized_schedule("dong")
st.header(f"🚇 지하철 시간표 ({mode_ban})")



col1, col2 = st.columns(2)
with col1:
    st.success("🚉 반야월 (상행)")
    st.caption("설화명곡 방면")
    if table_ban: st.table({"출발 예정": table_ban})
    else: st.write("운행 종료")

with col2:
    st.success("🚉 동대구 (하행)")
    st.caption("안심 방면")
    if table_dong: st.table({"출발 예정": table_dong})
    else: st.write("운행 종료")

if st.button('🔄 새로고침'):
    st.rerun()
