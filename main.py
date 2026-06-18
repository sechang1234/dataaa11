import streamlit as st
import pandas as pd
import numpy as np
import os

st.set_page_config(page_title="환율의 변화와 예측", layout="wide")

@st.cache_data
def load_data():
    file_path = "주요국 통화의 대원화 환율.csv"
    if not os.path.exists(file_path):
        return None
    encodings = ['utf-8', 'cp949', 'euc-kr', 'utf-8-sig']
    for enc in encodings:
        try:
            df = pd.read_csv(file_path, skiprows=8, names=['날짜', '원/달러', '원/100엔', '원/위안'], encoding=enc)
            df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
            df = df.dropna(subset=['날짜']).sort_values('날짜')
            for col in ['원/달러', '원/100엔', '원/위안']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        except:
            continue
    return None

df_raw = load_data()

if df_raw is None:
    st.error("⚠️ '주요국 통화의 대원화 환율.csv' 파일을 불러올 수 없습니다. 경로를 확인해 주세요.")
else:
    st.title("📈 환율의 변화와 예측")
    st.markdown("""
    본 대시보드는 주요국 통화(미국 달러, 일본 엔, 중국 위안)의 대원화 환율 데이터를 기반으로 합니다.
    과거부터 축적된 **환율의 역사적 변화 흐름을 추적**하고, 이를 통계적 모형으로 정량화하여 **미래의 변동 범위를 시뮬레이션**하는 탐구 목적의 웹 애플리케이션입니다.
    
    👈 왼쪽 사이드바의 메뉴를 클릭하여 각 통화별 상세 변화와 **2030년 장기 예측**을 확인해 보세요!
    """)
    
    st.sidebar.header("🔍 공통 분석 기간 설정")
    min_date, max_date = df_raw['날짜'].min().to_pydatetime(), df_raw['날짜'].max().to_pydatetime()
    start_date, end_date = st.sidebar.slider("기간 선택", min_value=min_date, max_value=max_date, value=(max_date - pd.Timedelta(days=365*2), max_date))
    
    df = df_raw[(df_raw['날짜'] >= start_date) & (df_raw['날짜'] <= end_date)].copy()
    df.set_index('날짜', inplace=True)
    currencies = ['원/달러', '원/100엔', '원/위안']
    
    st.header("📋 1. 최근 환율 변화 지표 및 통계 개요")
    cols = st.columns(3)
    for i, curr in enumerate(currencies):
        with cols[i]:
            valid_series = df[curr].dropna()
            if not valid_series.empty:
                st.metric(label=f"최근 {curr}", value=f"{valid_series.iloc[-1]:,.2f} 원")
                
    stats_df = df.describe().T[['count', 'mean', 'std', 'min', 'max']]
    stats_df.columns = ['관측치 개수', '평균값', '표준편차(변동성)', '최솟값', '최댓값']
    st.dataframe(stats_df.style.format("{:,.2f}"))
    
    st.header("🔗 2. 통화별 환율 변화의 연동성(상관관계) 검증")
    corr_matrix = df[currencies].corr(method='pearson')
    st.dataframe(corr_matrix.style.format("{:.4f}"))
