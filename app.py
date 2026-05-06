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
if selected_gu == '