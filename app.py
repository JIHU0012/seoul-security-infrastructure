import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import pydeck as pdk
import os

# ---------------------------------------------------------
# 1. 페이지 기본 설정 (와이드 레이아웃)
# ---------------------------------------------------------
st.set_page_config(page_title="서울특별시 치안 인프라 분석", page_icon="🚓", layout="wide")

# 다크 테마에 맞춘 세련된 커스텀 CSS 적용 및 제목 크기 조절
# 한 줄에 제목이 들어가도록 폰트 크기(font-size)를 조정했습니다.
st.markdown("""
    <style>
        .main-title {
            font-size: 2.2rem;
            font-weight: 800;
            color: #ffffff;
            white-space: nowrap; 
            margin-bottom: 0px;
        }
        .sub-title {
            font-size: 1.1rem;
            color: #a0aec0;
            margin-bottom: 30px;
        }
        .metric-box {
            background-color: #1e1e2d;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid #2d2d3f;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🚓 서울특별시 치안 인프라 & 범죄 분석 대시보드</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">자치구별 CCTV, 가로등, 비상벨 인프라와 범죄 발생 관계를 분석하여 치안 취약 지역을 발굴합니다.</p>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 데이터베이스 연결 및 데이터 로드
# ---------------------------------------------------------
@st.cache_data
def load_data():
    db_path = '서울안전.db'
    
    if not os.path.exists(db_path):
        st.error("🚨 앗! 데이터베이스 파일(`서울안전.db`)을 찾을 수 없습니다.")
        st.info("실행 중인 폴더 안에 데이터베이스 파일이 제대로 들어있는지 확인해주세요!")
        st.stop()
        
    conn = sqlite3.connect(db_path)
    df_analysis = pd.read_sql("SELECT * FROM 통합분석", conn)
    df_cctv = pd.read_sql("SELECT 자치구, WGS84위도, WGS84경도 FROM CCTV", conn)
    conn.close()
    
    # [파생 변수 생성]
    df_analysis['총_인프라수'] = df_analysis['CCTV수'] + df_analysis['가로등수'] + df_analysis['비상벨수']
    df_analysis['인프라당_범죄발생'] = df_analysis['총범죄_발생'] / df_analysis['총_인프라수'].replace(0, 1)
    
    return df_analysis, df_cctv

df_analysis, df_cctv = load_data()

# ---------------------------------------------------------
# 3. 사이드바 (자치구 선택 필터)
# ---------------------------------------------------------
st.sidebar.header("🔍 분석 옵션")
gu_list = ['전체'] + list(df_analysis['자치구'].unique())
selected_gu = st.sidebar.selectbox("자치구를 선택하세요", gu_list)

if selected_gu == '전체':
    filtered_analysis = df_analysis
    filtered_cctv = df_cctv
else:
    filtered_analysis = df_analysis[df_analysis['자치구'] == selected_gu]
    filtered_cctv = df_cctv[df_cctv['자치구'] == selected_gu]

# ---------------------------------------------------------
# 4. 핵심 지표 (다크 테마에 맞춘 메트릭 디자인)
# ---------------------------------------------------------
st.subheader(f"📌 {selected_gu} 치안 인프라 요약")

total_cctv = int(filtered_analysis['CCTV수'].sum())
total_light = int(filtered_analysis['가로등수'].sum())
total_bell = int(filtered_analysis['비상벨수'].sum())

col1, col2, col3 = st.columns(3)

# 어두운 배경에 네온 컬러 포인트를 주어 세련되게 표현
with col1:
    st.markdown(f"""
    <div class="metric-box">
        <h4 style="margin:0; color:#60A5FA;">📹 CCTV 수</h4>
        <h2 style="margin:0; color:#ffffff;">{total_cctv:,} 개</h2>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-box">
        <h4 style="margin:0; color:#FBBF24;">💡 가로등 수</h4>
        <h2 style="margin:0; color:#ffffff;">{total_light:,} 개</h2>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-box">
        <h4 style="margin:0; color:#F87171;">🚨 비상벨 수</h4>
        <h2 style="margin:0; color:#ffffff;">{total_bell:,} 개</h2>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. 지도 시각화 (서울 중심부 포커스 & 점 크기 축소)
# ---------------------------------------------------------
st.subheader(f"🗺️ {selected_gu} CCTV 분포 지도")

map_data = filtered_cctv[['WGS84위도', 'WGS84경도']].rename(
    columns={'WGS84위도': 'lat', 'WGS84경도': 'lon'}
)

# 데이터가 있을 때만 지도 생성
if not map_data.empty:
    # PyDeck을 사용하여 지도 초기 시점을 서울(위도 37.56, 경도 126.98)로 고정하고 줌 레벨 조정
    view_state = pdk.ViewState(
        latitude=37.5665 if selected_gu == '전체' else map_data['lat'].mean(),
        longitude=126.9780 if selected_gu == '전체' else map_data['lon'].mean(),
        zoom=10.5 if selected_gu == '전체' else 13, # 전체면 넓게, 특정 구면 줌 인
        pitch=0
    )
    
    # 점의 크기와 투명도 조절 (get_radius로 반경 축소, get_fill_color로 예쁜 빨간색 설정)
    layer = pdk.Layer(
        'ScatterplotLayer',
        data=map_data,
        get_position='[lon, lat]',
        get_radius=25, # 기존보다 훨씬 작고 촘촘하게 설정
        get_fill_color='[255, 75, 75, 180]',
        pickable=True
    )
    
    # 다크 테마 맵 적용 (map_style='dark')
    st.pydeck_chart(pdk.Deck(
        map_style='dark', 
        initial_view_state=view_state,
        layers=[layer],
        tooltip={"text": "CCTV 위치"}
    ))
else:
    st.warning("해당 지역의 CCTV 위치 데이터가 존재하지 않습니다.")

st.markdown("---")

# ---------------------------------------------------------
# 6. 인사이트 분석 (Plotly Dark 테마 적용)
# ---------------------------------------------------------
st.subheader("📊 치안 인프라 및 범죄 심층 분석")

row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    st.markdown("**📉 인프라수 대비 범죄 발생 건수 (전체)**")
    fig_scatter = px.scatter(
        df_analysis, 
        x='총_인프라수', 
        y='총범죄_발생', 
        color='자치구',
        size='인프라당_범죄발생',
        hover_data=['인프라당_범죄발생'],
        trendline="ols", 
        template="plotly_dark" # 차트 배경을 다크 테마로 변경
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with row1_col2:
    st.markdown("**🏆 치안 인프라 우수 지역 TOP 5**")
    top5_infra = df_analysis.sort_values(by='총_인프라수', ascending=False).head(5)
    
    fig_bar1 = px.bar(
        top5_infra, 
        x='자치구', 
        y='총_인프라수', 
        text='총_인프라수',
        color='총_인프라수',
        color_continuous_scale='Blues',
        template="plotly_dark"
    )
    fig_bar1.update_traces(textposition='outside')
    st.plotly_chart(fig_bar1, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 7. 치안 인프라 확충 시급 지역
# ---------------------------------------------------------
st.subheader("🚨 치안 인프라 확충 시급 지역")
row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    st.markdown("**⚠️ 인프라 확충 시급 지역 TOP 5**")
    urgent_top5 = df_analysis.sort_values(by='인프라당_범죄발생', ascending=False).head(5)
    urgent_top5['인프라당_범죄발생'] = urgent_top5['인프라당_범죄발생'].round(2)
    
    fig_bar2 = px.bar(
        urgent_top5, 
        x='자치구', 
        y='인프라당_범죄발생', 
        text='인프라당_범죄발생',
        color='인프라당_범죄발생',
        color_continuous_scale='Reds',
        template="plotly_dark"
    )
    fig_bar2.update_traces(textposition='outside')
    st.plotly_chart(fig_bar2, use_container_width=True)

with row2_col2:
    st.markdown("**💡 데이터 인사이트 요약**")
    st.info(
        """
        - **인프라당 범죄발생 지표**는 치안 인프라 1개당 발생한 범죄 건수입니다.
        - 산점도에서 원의 크기가 크고 추세선 위에 있는 지역, 그리고 아래 붉은색 그래프의 **TOP 5 지역**은 방범 인프라가 절대적으로 부족한 상태입니다.
        - **우선 정책 제안:** 해당 자치구(TOP 5)에 예산을 집중 편성하여 CCTV와 비상벨을 최우선적으로 설치해야 합니다.
        """
    )