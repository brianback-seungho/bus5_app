import streamlit as st
import requests
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="동구5 & 지하철 안내판", page_icon="🚌", layout="centered")

# 2. 인증키 설정 (버스 전용)
# 공공데이터포털에서 발급받은 본인의 인증키를 아래에 입력하세요.
SERVICE_KEY = "6fc222f7a07ce61876bf07b46533721a192b38b26b2ff8aff34d8bdc837f5ba1"

# 3. 데이터 로드 함수 (버스 전용)
def get_bus_data(bsId):
    url = "http://apis.data.go.kr/6270000/dbmsapi02/getRealtime02"
    params = {
        'serviceKey': requests.utils.unquote(SERVICE_KEY).strip(),
        'bsId': bsId,
        'numOfRows': '20',
        'pageNo': '1',
        '_type': 'json'
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            return res.json().get('body', {}).get('items', [])
        return []
    except:
        return []

# --- UI 시작 ---
st.title("🚌 통합 교통 안내판")
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"최종 업데이트: {now}")

# 새로고침 버튼
if st.button('🔄 정보 새로고침', use_container_width=True):
    st.rerun()

# [섹션 1] 실시간 버스 정보 (동구5)
st.header("🚏 실시간 버스 (동구5)")

bus_stations = [
    {'name': '📍 율하고가교1', 'id': '7011061400'},
    {'name': '📍 항공교통본부앞', 'id': '7011060900'}
]

for bs in bus_stations:
    with st.expander(bs['name'], expanded=True):
        items = get_bus_data(bs['id'])
        found = False
        if items:
            for item in items:
                # '동구5'라는 글자가 노선번호에 포함된 경우만 필터링
                if '동구5' in str(item.get('routeNo', '')):
                    arr_list = item.get('arrList', [])
                    if arr_list:
                        for bus in arr_list:
                            st.metric(label="도착 예정", value=bus.get('arrState'))
                            st.write(f"🚩 현재 위치: **{bus.get('bsNm')}**")
                            found = True
        
        if not found:
            st.info("현재 진입 중인 동구5번 버스가 없습니다.")

# [섹션 2] 지하철 시간표 (대구 1호선)
st.divider()
st.header("🚇 지하철 시간표")
st.write("가장 정확한 대구교통공사 실시간 시간표로 연결됩니다.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🚉 반야월역")
    st.caption("방면: 설화명곡 (상행)")
    # 반야월역 코드: 144, 상행 코드: 1
    banyawol_url = "https://www.dtro.or.kr/open_content_new/ko/OpenApi/stationTime.php?station_code=144&up_down=1"
    st.link_button("반야월역 시간표 보기", banyawol_url, use_container_width=True)

with col2:
    st.subheader("🚉 동대구역")
    st.caption("방면: 안심 (하행)")
    # 동대구역 코드: 135, 하행 코드: 2
    dongdaegu_url = "https://www.dtro.or.kr/open_content_new/ko/OpenApi/stationTime.php?station_code=135&up_down=2"
    st.link_button("동대구역 시간표 보기", dongdaegu_url, use_container_width=True)

st.divider()
st.caption("출처: 대구광역시 버스정보시스템, 대구교통공사 DTRO")
