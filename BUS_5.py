import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="동구5 & 지하철 안내판", page_icon="🚌")

# 2. 인증키 (본인의 것으로 변경)
SERVICE_KEY = "6fc222f7a07ce61876bf07b46533721a192b38b26b2ff8aff34d8bdc837f5ba1"

# 3. 한국 시간 강제 설정 함수
def get_now_korea():
    # 서버 시간이 어디든 한국 시간(UTC+9)으로 계산
    return datetime.utcnow() + timedelta(hours=9)

# 4. 버스 데이터 함수
def get_bus_data(bsId):
    url = "http://apis.data.go.kr/6270000/dbmsapi02/getRealtime02"
    params = {'serviceKey': requests.utils.unquote(SERVICE_KEY).strip(), 'bsId': bsId, 'numOfRows': '20', '_type': 'json'}
    try:
        res = requests.get(url, params=params, timeout=5)
        return res.json().get('body', {}).get('items', [])
    except: return []

# 5. 지하철 시간표 파싱 함수 (경로 보강)
def get_subway_table(station_code, up_down):
    url = f"https://www.dtro.or.kr/open_content_new/ko/OpenApi/stationTime.php?station_code={station_code}&up_down={up_down}"
    
    # 브라우저처럼 보이게 만드는 헤더
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # SSL 인증서 무시(verify=False) 및 헤더 추가
        res = requests.get(url, headers=headers, timeout=10, verify=False)
        res.encoding = 'utf-8'
        
        # 만약 데이터가 너무 짧으면(에러 페이지 등) 빈 리스트 반환
        if len(res.text) < 100:
            return []
            
        root = ET.fromstring(res.text)
        times = []
        
        # 'item' 태그를 더 공격적으로 찾음
        for item in root.iter('item'):
            hh = item.findtext('stime_hh')
            mm = item.findtext('stime_mm')
            if hh and mm:
                times.append(f"{hh.strip().zfill(2)}:{mm.strip().zfill(2)}")
        
        if not times:
            return []
            
        # 한국 시간 기준으로 필터링
        now_str = (datetime.utcnow() + timedelta(hours=9)).strftime("%H:%M")
        upcoming = [t for t in sorted(list(set(times))) if t >= now_str]
        
        return upcoming[:5]
    except Exception as e:
        # 디버깅용: 실제 화면에 에러가 살짝 찍히게 함 (나중에 지워도 됨)
        # st.write(f"로그: {str(e)}")
        return []

# --- UI 시작 ---
st.title("🚌 통합 교통 안내판")
# 현재 한국 시간 표시
st.write(f"🇰🇷 현재 시각: **{get_now_korea().strftime('%H:%M:%S')}**")

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
    table = get_subway_table('144', '1')
    if table: st.table({"출발 시각": table})
    else: st.write("운행 정보 없음")

with col2:
    st.subheader("🚉 동대구 (하행)")
    st.caption("안심 방면")
    table = get_subway_table('135', '2')
    if table: st.table({"출발 시각": table})
    else: st.write("운행 정보 없음")

if st.button('🔄 정보 업데이트'):
    st.rerun()

