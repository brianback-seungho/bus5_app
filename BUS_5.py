import streamlit as st
import requests
from datetime import datetime, timedelta

# ---------------------------------------------------------
# [중요] 여기에 본인의 인증키를 붙여넣으세요!
# ---------------------------------------------------------
MY_SERVICE_KEY = "6fc222f7a07ce61876bf07b46533721a192b38b26b2ff8aff34d8bdc837f5ba1" 
# ---------------------------------------------------------

st.set_page_config(page_title="동구5 & 지하철 도착시간", page_icon="🚌")

# 한국 시간 설정 함수
def get_now_korea():
    return datetime.utcnow() + timedelta(hours=9)

# 실시간 버스 데이터 가져오기 함수
def get_bus_data(bsId):
    # 전역 변수 MY_SERVICE_KEY를 사용합니다.
    url = f"http://apis.data.go.kr/6270000/dbmsapi02/getRealtime02?serviceKey={MY_SERVICE_KEY}&bsId={bsId}&_type=json"
    try:
        res = requests.get(url, timeout=5)
        # 결과가 잘 왔는지 확인
        if res.status_code == 200:
            return res.json().get('body', {}).get('items', [])
        return []
    except:
        return []

# 지하철 가상 시간표 (10분 간격 패턴 생성)
def get_offline_subway():
    now_str = get_now_korea().strftime("%H:%M")
    base_times = []
    for h in range(5, 24):
        for m in [5, 15, 25, 35, 45, 55]:
            base_times.append(f"{str(h).zfill(2)}:{str(m).zfill(2)}")
    upcoming = [t for t in sorted(list(set(base_times))) if t >= now_str]
    return upcoming[:5]

# --- 화면 구성 시작 ---
st.title("🚌 통합 교통 안내판")
st.subheader(f"🇰🇷 현재 시각: {get_now_korea().strftime('%H:%M:%S')}")

# [버스 섹션]
st.header("🚏 실시간 버스 (동구5)")

bus_stations = [
    {'name': '📍 율하고가교1', 'id': '7011061400'}, 
    {'name': '📍 항공교통본부앞', 'id': '7011060900'}
]

for bs in bus_stations:
    with st.expander(bs['name'], expanded=True):
        # 함수를 부를 때 아이디만 주면, 함수가 알아서 위쪽의 키를 가져다 씁니다.
        data = get_bus_data(bs['id'])
        found = False
        if data:
            for item in data:
                if '동구5' in str(item.get('routeNo', '')):
                    arr_list = item.get('arrList', [])
                    if arr_list:
                        for bus in arr_list:
                            st.metric(label="버스 도착 예정", value=bus.get('arrState'))
                            st.write(f"🚩 현재 위치: **{bus.get('bsNm')}**")
                            found = True
        if not found:
            st.info("현재 진입 중인 동구5번 버스가 없습니다.")

# [지하철 섹션]
st.divider()
st.header("🚇 지하철 시간표 (이후 열차)")

col1, col2 = st.columns(2)
subway_times = get_offline_subway()

with col1:
    st.success("🚉 반야월 (상행)")
    st.caption("설화명곡 방면")
    if subway_times:
        st.table({"출발 예정": subway_times})
    else: st.write("운행 종료")

with col2:
    st.success("🚉 동대구 (하행)")
    st.caption("안심 방면")
    if subway_times:
        st.table({"출발 예정": subway_times})
    else: st.write("운행 종료")

if st.button('🔄 새로고침'):
    st.rerun()
