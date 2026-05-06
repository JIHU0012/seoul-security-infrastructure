import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# ---------------------------------------------------------
# 1. 페이지 기본 설정 (큰 제목 변경)
# ---------------------------------------------------------
st.set_page_config(page_title="서울특별시 치안 인프라 & 범죄 분석 대시보드", page_icon="🚓", layout="wide")
st.title("🚓 서울특별시 치안 인프라 & 범죄 분석 대시보드")
st.markdown("자치구별 CCTV, 가로등, 비상벨 등 치안 인프라와 범죄 발생 간의 관계를 분석하여 **치안 취약 지역**을 발굴합니다.")

# ---------------------------------------------------------
# 2. 데이터베이스 연결 및 데이터 로드
# ---------------------------------------------------------
@st.cache_data
def load_data():
    db_path = '서울안전.db'
    
    # DB 파일이 없을 경우 친절한 에러 메시지 출력
    if not os.path.exists(db_path):
        st.error("🚨 앗! 데이터베이스 파일(`서울안전.db` 또는 `bicycle.db`)을 찾을 수 없습니다.")
        st.info("실행 중인 폴더(디렉토리) 안에 데이터베이스 파일이 제대로 들어있는지 확인해주세요!")
        st.stop() # 더 이상 코드를 실행하지 않고 멈춥니다.
        
    # SQLite DB 연결 및 테이블 불러오기
    conn = sqlite3.connect(db_path)
    df_analysis = pd.read_sql("SELECT * FROM 통합분석", conn)
    df_cctv = pd.read_sql("SELECT 자치구, WGS84위도, WGS84경도 FROM CCTV", conn)
    conn.close()
    
    #[파생 변수 생성]
    # 총_인프라수 = 자치구별 가로등 + 비상벨 + CCTV 합계 (안전 자원 규모)
    df_analysis['총_인프라수'] = df_analysis['CCTV수'] + df_analysis['가로등수'] + df_analysis['비상벨수']
    
    # 인프라당_범죄발생 = 총범죄 / 총_인프라수 
    # (이 수치가 높을수록 인프라에 비해 범죄가 많아 '인프라 확충이 시급한 지역'입니다)
    df_analysis['인프라당_범죄발생'] = df_analysis['총범죄_발생'] / df_analysis['총_인프라수'].replace(0, 1)
    
    return df_analysis, df_cctv

df_analysis, df_cctv = load_data()

# ---------------------------------------------------------
# 3. 사이드바 (자치구 선택 필터)
# ---------------------------------------------------------
st.sidebar.header("🔍 분석 옵션")
gu_list = ['전체'] + list(df_analysis['자치구'].unique())
selected_gu = st.sidebar.selectbox("자치구를 선택하세요", gu_list)

# 선택한 자치구 데이터만 걸러내기 (필터링)
# --- 에러가 났던 부분입니다! 글자가 잘리지 않게 주의해주세요 ---
if selected_gu == '전체':
    filtered_analysis = df_analysis
    filtered_cctv = df_cctv
else:
    filtered_analysis = df_analysis[df_analysis['자치구'] == selected_gu]
    filtered_cctv = df_cctv[df_cctv['자치구'] == selected_gu]
# ------------------------------------------------------------------

# ---------------------------------------------------------
# 4. 핵심 지표 (가시성 대폭 강화)
# ---------------------------------------------------------
st.subheader(f"📌 {selected_gu} 치안 인프라 요약")

total_cctv = int(filtered_analysis['CCTV수'].sum())
total_light = int(filtered_analysis['가로등수'].sum())
total_bell = int(filtered_analysis['비상벨수'].sum())

# HTML/CSS를 활용해 배경색과 둥근 테두리가 있는 눈에 띄는 박스 만들기
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div style="background-color:#E8F0FE; padding:20px; border-radius:10px; text-align:center; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);">
        <h3 style="margin:0; color:#1A73E8;">📹 CCTV 수</h3>
        <h2 style="margin:0; color:#333;">{total_cctv:,} 개</h2>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div style="background-color:#FEF7E0; padding:20px; border-radius:10px; text-align:center; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);">
        <h3 style="margin:0; color:#F9AB00;">💡 가로등 수</h3>
        <h2 style="margin:0; color:#333;">{total_light:,} 개</h2>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div style="background-color:#FCE8E6; padding:20px; border-radius:10px; text-align:center; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);">
        <h3 style="margin:0; color:#EA4335;">🚨 비상벨 수</h3>
        <h2 style="margin:0; color:#333;">{total_bell:,} 개</h2>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True) # 줄바꿈 여백

# ---------------------------------------------------------
# 5. 지도 시각화 (CCTV 위치)
# ---------------------------------------------------------
st.subheader(f"🗺️ {selected_gu} CCTV 위치 지도")
map_data = filtered_cctv[['WGS84위도', 'WGS84경도']].rename(
    columns={'WGS84위도': 'lat', 'WGS84경도': 'lon'}
)

if not map_data.empty:
    st.map(map_data)
else:
    st.warning("해당 지역의 CCTV 위치 데이터가 존재하지 않습니다.")

st.markdown("---")

# ---------------------------------------------------------
# 6. 인사이트 분석 (인프라 vs 범죄율 심층 분석)
# ---------------------------------------------------------
st.subheader("📊 치안 인프라 및 범죄 심층 분석")

# 첫 번째 줄: 인프라가 잘 된 곳 vs 전체 추세 시각화
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    st.markdown("**📉 인프라수 대비 범죄 발생 건수 (전체 자치구)**")
    fig_scatter = px.scatter(
        df_analysis, 
        x='총_인프라수', 
        y='총범죄_발생', 
        color='자치구',
        size='인프라당_범죄발생', # 원의 크기로 인프라 부족 심각성 표현
        hover_data=['인프라당_범죄발생'],
        trendline="ols", 
        title="인프라가 많을수록 범죄는 줄어들까?"
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
    st.info("💡 **인사이트:** 산점도에서 점이 추세선보다 **위쪽에 위치**하면서 **원의 크기가 클수록**, 인프라 대비 범죄율이 높아 대책이 시급한 지역입니다.")

with row1_col2:
    st.markdown("**🏆 치안 인프라 우수 지역 TOP 5**")
    # 총_인프라수가 가장 많은 상위 5개 지역
    top5_infra = df_analysis.sort_values(by='총_인프라수', ascending=False).head(5)
    
    fig_bar1 = px.bar(
        top5_infra, 
        x='자치구', 
        y='총_인프라수', 
        text='총_인프라수',
        color='총_인프라수',
        color_continuous_scale='Blues',
        title="가장 인프라가 잘 구축된 자치구 TOP 5"
    )
    fig_bar1.update_traces(textposition='outside')
    st.plotly_chart(fig_bar1, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# 두 번째 줄: 인프라 확충 시급 지역 집중 조명
st.subheader("🚨 치안 인프라 확충 시급 지역 (범죄 대비 인프라 부족)")
row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    st.markdown("**⚠️ 인프라 확충 시급 지역 TOP 5**")
    # '인프라당_범죄발생' 수치가 가장 높은 상위 5개 지역 (범죄는 많은데 인프라는 적은 곳)
    urgent_top5 = df_analysis.sort_values(by='인프라당_범죄발생', ascending=False).head(5)
    
    # 소수점 둘째자리까지만 보이도록 반올림
    urgent_top5['인프라당_범죄발생'] = urgent_top5['인프라당_범죄발생'].round(2)
    
    fig_bar2 = px.bar(
        urgent_top5, 
        x='자치구', 
        y='인프라당_범죄발생', 
        text='인프라당_범죄발생',
        color='인프라당_범죄발생',
        color_continuous_scale='Reds', # 위험을 나타내기 위해 붉은색 계열 사용
        title="인프라 1개당 범죄 발생 건수가 가장 높은 지역 TOP 5"
    )
    fig_bar2.update_traces(textposition='outside')
    st.plotly_chart(fig_bar2, use_container_width=True)

with row2_col2:
    st.markdown("**💡 데이터 인사이트 요약**")
    st.warning(
        """
        - **인프라당 범죄발생 지표**는 치안 인프라(가로등+비상벨+CCTV) 1개당 발생한 범죄 건수를 의미합니다.
        - 위 붉은색 그래프의 **TOP 5 지역**은 범죄 발생량에 비해 방범 인프라가 절대적으로 부족한 상태입니다.
        - **우선 정책 제안:** 해당 자치구들에 예산을 집중 편성하여 CCTV와 비상벨을 최우선적으로 설치해야 시민 안전을 빠르게 개선할 수 있습니다.
        """
    )