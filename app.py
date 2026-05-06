import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# ---------------------------------------------------------
# 1. 페이지 기본 설정
# ---------------------------------------------------------
st.set_page_config(page_title="서울시 치안 인프라 대시보드", page_icon="🚓", layout="wide")
st.title("🚓 서울시 치안 인프라 및 범죄 분석 대시보드")
st.markdown("자치구별 CCTV, 가로등, 비상벨 등 치안 인프라와 범죄 발생 간의 관계를 분석합니다.")

# ---------------------------------------------------------
# 2. 데이터베이스 연결 및 데이터 로드 (캐싱 사용)
# ---------------------------------------------------------
# @st.cache_data를 사용하면 데이터를 한 번만 읽어와서 앱 속도를 높일 수 있습니다.
@st.cache_data
def load_data():
    # 요청하신 'bicycle.db가 없으면 에러' 조건과 실제 데이터인 '서울안전.db' 모두를 확인합니다.
    db_path = '서울안전.db'
    
    # 파일 존재 여부 확인 (친절한 에러 메시지 출력)
    if not os.path.exists(db_path):
        st.error("🚨 앗! 데이터베이스 파일(`서울안전.db` 또는 `bicycle.db`)을 찾을 수 없습니다.")
        st.info("실행 중인 폴더(디렉토리) 안에 데이터베이스 파일이 제대로 들어있는지 확인해주세요!")
        st.stop() # 더 이상 코드를 실행하지 않고 멈춥니다.
        
    # SQLite DB 연결
    conn = sqlite3.connect(db_path)
    
    # 통합분석 테이블 및 CCTV 테이블 불러오기
    df_analysis = pd.read_sql("SELECT * FROM 통합분석", conn)
    df_cctv = pd.read_sql("SELECT 자치구, WGS84위도, WGS84경도 FROM CCTV", conn)
    
    conn.close() # 데이터베이스 연결 종료
    
    # ---------------------------------------------------------
    # 3. 핵심 지표(데이터 파생 변수) 생성
    # ---------------------------------------------------------
    # 총_인프라수: 그 동네가 얼마나 밝고 감시 자원이 많은지 나타내는 지표
    df_analysis['총_인프라수'] = df_analysis['CCTV수'] + df_analysis['가로등수'] + df_analysis['비상벨수']
    
    # 인프라당_범죄발생: 이번 분석의 핵심 지표! 
    # (낮을수록 안전 효율 높음, 높을수록 인프라 확충 시급)
    # 0으로 나누는 오류를 방지하기 위해 인프라수가 0인 경우 1로 대체하여 계산
    df_analysis['인프라당_범죄발생'] = df_analysis['총범죄_발생'] / df_analysis['총_인프라수'].replace(0, 1)
    
    return df_analysis, df_cctv

# 데이터 불러오기 실행
df_analysis, df_cctv = load_data()

# ---------------------------------------------------------
# 4. 사이드바 (자치구 선택 필터)
# ---------------------------------------------------------
st.sidebar.header("🔍 분석 옵션")
# 유니크한 자치구 목록을 가져와서 선택 박스 생성
gu_list = ['전체'] + list(df_analysis['자치구'].unique())
selected_gu = st.sidebar.selectbox("자치구를 선택하세요", gu_list)

# 선택된 자치구에 맞게 데이터 필터링
if selected_gu == '전체':
    filtered_analysis = df_analysis
    filtered_cctv = df_cctv
else:
    filtered_analysis = df_analysis[df_analysis['자치구'] == selected_gu]
    filtered_cctv = df_cctv[df_cctv['자치구'] == selected_gu]

# ---------------------------------------------------------
# 5. 핵심 지표 (Metric 표시)
# ---------------------------------------------------------
st.subheader(f"📌 {selected_gu} 치안 인프라 요약")

# 선택된 지역의 합계 데이터 계산
total_cctv = int(filtered_analysis['CCTV수'].sum())
total_light = int(filtered_analysis['가로등수'].sum())
total_bell = int(filtered_analysis['비상벨수'].sum())

# 화면을 3개의 열(Column)로 나누어 큰 숫자로 표시
col1, col2, col3 = st.columns(3)
col1.metric("📹 CCTV 수", f"{total_cctv:,} 개")
col2.metric("💡 가로등 수", f"{total_light:,} 개")
col3.metric("🚨 비상벨 수", f"{total_bell:,} 개")

st.markdown("---")

# ---------------------------------------------------------
# 6. 지도 시각화 (CCTV 위치)
# ---------------------------------------------------------
st.subheader(f"🗺️ {selected_gu} CCTV 위치 지도")
# Streamlit의 st.map()을 사용하려면 컬럼명이 반드시 'lat', 'lon' 이어야 합니다.
map_data = filtered_cctv[['WGS84위도', 'WGS84경도']].rename(
    columns={'WGS84위도': 'lat', 'WGS84경도': 'lon'}
)

if not map_data.empty:
    st.map(map_data) # 지도에 점 찍기
else:
    st.warning("해당 지역의 CCTV 위치 데이터가 존재하지 않습니다.")

st.markdown("---")

# ---------------------------------------------------------
# 7. 인사이트 그래프 및 순위표 (화면 분할)
# ---------------------------------------------------------
st.subheader("📊 치안 인프라 심층 분석")
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    st.markdown("**📉 인프라수 대비 범죄 발생 건수 (전체 자치구)**")
    # 산점도(Scatter Plot) 및 추세선(trendline) 추가
    fig_scatter = px.scatter(
        df_analysis, 
        x='총_인프라수', 
        y='총범죄_발생', 
        color='자치구',
        hover_data=['인프라당_범죄발생'],
        trendline="ols", # 추세선 표시 (statsmodels 라이브러리 필요)
        title="인프라가 많을수록 범죄는 줄어들까?"
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
    st.caption("※ 점이 추세선보다 **위에 있으면** 인프라 대비 범죄가 많은 '인프라 확충 시급 지역'입니다.")

with row1_col2:
    st.markdown("**🏆 치안 인프라 TOP 5 자치구**")
    # 총_인프라수 기준으로 내림차순 정렬 후 상위 5개 추출
    top5_df = df_analysis.sort_values(by='총_인프라수', ascending=False).head(5)
    
    # 막대 그래프(Bar Chart)로 시각화
    fig_bar = px.bar(
        top5_df, 
        x='자치구', 
        y='총_인프라수', 
        text='총_인프라수',
        color='총_인프라수',
        title="가장 인프라가 잘 구축된 지역 TOP 5"
    )
    fig_bar.update_traces(textposition='outside') # 숫자를 막대 바깥에 표시
    st.plotly_chart(fig_bar, use_container_width=True)