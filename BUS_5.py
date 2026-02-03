import streamlit as st
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="동구5 & 지하철 도착 시간", page_icon="🚌")

# 인증키 (본인의 것으로 변경)
SERVICE_KEY = "6fc222f7a07ce61876bf07b46533721a192b38b26b2ff8aff34d8bdc837f5ba1"

# 1. 한국 시간 설정
def get_now_korea():
    return datetime.utcnow() + timedelta(hours=9)

# 2. 버스 데이터를 가져오는 함수 (이 키를 사용합니다)
def get_bus_data(bsId):
    # 위에서 정의한 SERVICE_KEY를 사용함
    url = f"http://apis.data.go.kr/6270000/dbmsapi02/getRealtime02?serviceKey={SERVICE_KEY}&bsId={bsId}&_type=json"
    try:
        res = requests.get(url, timeout=5)
        return res.json().get('body', {}).get('items', [])
    except:
        return []

# 3. 지하철 내장 시간표 (평일 주요 시간대 샘플 데이터)
# 실제 시간을 모두 넣기엔 양이 많아, 로직을 보여드리기 위해 패턴화했습니다.
def get_offline_subway(station):
    now = get_now_korea()
    now_str = now.strftime("%H:%M")
    
    # 예시 데이터: 10분 간격으로 열차가 있다고 가정 (실제 시간표와 유사하게 자동 생성)
    # 실제 정확한 시간표 데이터를 리스트로 넣으셔도 됩니다.
    base_times = []
    for h in range(5, 24):
        for m in [5, 15, 25, 35, 45, 55]: # 대략적인 배차 간격
            base_times.append(f"{str(h).zfill(2)}:{str(m).zfill(2)}")
    
    upcoming = [t for t in base_times if t >= now_str]
    return upcoming[:5]

# --- UI 시작 ---
st.title("🚌 통합 교통 안내판")
st.subheader(f"🇰🇷 현재 시각: {get_now_korea().strftime('%H:%M:%S')}")

# [버스 섹션]
st.header("🚏 실시간 버스 (동구5)")
MY_KEY = "사용자님의_인증키" # 여기에 본인 키를 꼭 넣으세요!

bus_stations = [{'name': '📍 율하고가교1', 'id': '7011061400'}, {'name': '📍 항공교통본부앞', 'id': '7011060900'}]

for bs in bus_stations:
    with st.expander(bs['name'], expanded=True):
        data = get_bus_data(bs['id'], MY_KEY)
        found = False
        if data:
            for item in data:
                if '동구5' in str(item.get('routeNo', '')):
                    for bus in item.get('arrList', []):
                        st.metric(label="버스 도착 예정", value=bus.get('arrState'))
                        st.write(f"🚩 현재 위치: **{bus.get('bsNm')}**")
                        found = True
        if not found: st.info("진입 중인 동구5번 없음")

# [지하철 섹션]
st.divider()
st.header("🚇 지하철 시간표 (오늘)")

col1, col2 = st.columns(2)

with col1:
    st.success("🚉 반야월 (상행)")
    st.caption("설화명곡 방면")
    table = get_offline_subway("Banyawol")
    st.table({"출발 예정": table})

with col2:
    st.success("🚉 동대구 (하행)")
    st.caption("안심 방면")
    table = get_offline_subway("Dongdaegu")
    st.table({"출발 예정": table})

if st.button('🔄 새로고침'):
    st.rerun()

