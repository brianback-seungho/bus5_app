import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="동구5 & 지하철 안내판", page_icon="🚌")

# 2. 인증키 (버스용)
SERVICE_KEY = "6fc222f7a07ce61876bf07b46533721a192b38b26b2ff8aff34d8bdc837f5ba1"

# 3. 버스 데이터 함수
def get_bus_data(bsId):
    url = "http://apis.data.go.kr/6270000/dbmsapi02/getRealtime02"
    params = {'serviceKey': requests.utils.unquote(SERVICE_KEY).strip(), 'bsId': bsId, 'numOfRows': '20', '_type': 'json'}
    try:
        res = requests.get(url, params=params, timeout=5)
        return res.json().get('body', {}).get('items', [])
    except: return []

# 4. 지하철 시간표 가져와서 해석(Parsing)하는 함수
def get_subway_table(station_code, up_down):
    url = f"https://www.dtro.or.kr/open_content_new/ko/OpenApi/stationTime.php?station_code={station_code}&up_down={up_down}"
    try:
        res = requests.get(url, timeout=5)
        root = ET.fromstring(res.text)
        
        times = []
        for item in root.findall('.//item'):
            h = item.find('stime_hh').text.zfill(2)
            m = item.find('stime_mm').text.zfill(2)
            times.append(f"{h}:{m}")
        
        # 현재 시간 이후의 시간만 필터링
        now = datetime.now().strftime("%H:%M")
        next_trains = [t for t in sorted(times) if t >= now]
        return next_trains[:5] # 다음 열차 5개만 반환
    except:
        return []

# --- UI 시작 ---
st.title("🚌 통합 교통 안내판")
st.caption(f"현재 시각: {datetime.now().strftime('%H:%M:%S')}")

# [버스 섹션]
st.header("🚏 실시간 버스 (동구5)")
bus_stations = [{'name': '📍 율하고가교1', 'id': '7011061400'}, {'name': '📍 항공교통본부앞', 'id': '7011060900'}]

for bs in bus_stations:
    with st.expander(bs['name'], expanded=True):
        items = get_bus_data(bs['id'])
        found = False
        if items:
            for item in items:
                if '동구5' in str(item.get('routeNo', '')):
                    for bus in item.get('arrList', []):
                        st.metric(label="버스 도착 예정", value=bus.get('arrState'))
                        st.write(f"현재 위치: {bus.get('bsNm')}")
                        found = True
        if not found: st.write("진입 중인 버스 없음")

# [지하철 섹션]
st.divider()
st.header("🚇 지하철 시간표 (이후 열차)")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🚉 반야월 (상행)")
    st.caption("설화명곡 방면")
    table = get_subway_table('144', '1') # 반야월 상행
    if table:
        st.table({"출발 시간": table})
    else: st.write("운행 종료")

with col2:
    st.subheader("🚉 동대구 (하행)")
    st.caption("안심 방면")
    table = get_subway_table('135', '2') # 동대구 하행
    if table:
        st.table({"출발 시간": table})
    else: st.write("운행 종료")

if st.button('🔄 정보 업데이트'):
    st.rerun()999
