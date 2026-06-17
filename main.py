import streamlit as st
import pandas as pd
import numpy as np
import os

# 1. 웹앱 전체 환경 설정
st.set_page_config(page_title="원화 환율 변동 추이 분석", layout="wide")

# 2. 데이터 자동 로드 기능 (캐싱 적용)
@st.cache_data
def load_data_from_file(file_path):
    encodings = ['utf-8', 'cp949', 'euc-kr', 'utf-8-sig']
    df = None
    for enc in encodings:
        try:
            df = pd.read_csv(file_path, skiprows=8, names=['날짜', '원/달러', '원/100엔', '원/위안'], encoding=enc)
            break
        except:
            continue
    
    if df is None:
        raise ValueError("파일의 인코딩을 지원하지 않습니다.")
    
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
    df = df.dropna(subset=['날짜']).sort_values('날짜')
    
    for col in ['원/달러', '원/100엔', '원/위안']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return df

FILE_NAME = "주요국 통화의 대원화 환율.csv"
df_raw = None

if os.path.exists(FILE_NAME):
    try:
        df_raw = load_data_from_file(FILE_NAME)
    except Exception as e:
        st.error(f"데이터 파일 전처리 중 오류: {e}")
else:
    st.error(f"⚠️ 깃허브 저장소에 '{FILE_NAME}' 파일이 존재하지 않습니다.")

# 데이터가 성공적으로 로드된 경우에만 대시보드 실행
if df_raw is not None:
    
    # 3. 사이드바 내비게이션 (멀티 페이지 메뉴)
    st.sidebar.header("🗺️ 페이지 이동")
    page = st.sidebar.radio(
        "분석할 국가를 선택하세요",
        ["🏠 홈 (종합 분석)", "🇺🇸 미국 (원/달러)", "🇯🇵 일본 (원/100엔)", "🇨🇳 중국 (원/위안)"]
    )
    
    # 4. 사이드바 - 분석 기간 공통 설정
    st.sidebar.header("🔍 분석 설정")
    min_date = df_raw['날짜'].min().to_pydatetime()
    max_date = df_raw['날짜'].max().to_pydatetime()
    
    start_date, end_date = st.sidebar.slider(
        "분석 기간 선택",
        min_value=min_date,
        max_value=max_date,
        value=(max_date - pd.Timedelta(days=365*2), max_date)
    )
    
    # 기간 필터링 데이터 생성
    df = df_raw[(df_raw['날짜'] >= start_date) & (df_raw['날짜'] <= end_date)].copy()
    df.set_index('날짜', inplace=True)
    currencies = ['원/달러', '원/100엔', '원/위안']
    
    # 변동률 및 히스토그램 데이터 선행 계산
    return_df = df[currencies].pct_change() * 100
    return_df_clean = return_df.dropna()
    
    # ==========================================
    # PAGE 1: 홈 (종합 분석)
    # ==========================================
    if page == "🏠 홈 (종합 분석)":
        st.title("📈 주요국 통화의 대원화 환율 변동 추이 및 통계적 분석")
        st.markdown("본 대시보드는 미국 달러, 일본 엔, 중국 위안화의 대원화 환율 데이터를 기반으로 한 통계 탐구 보고서입니다.")
        
        # 최근 환율 모니터링
        st.header("📋 1. 최근 환율 및 기술 통계 개요")
        cols = st.columns(3)
        for i, curr in enumerate(currencies):
            with cols[i]:
                valid_series = df[curr].dropna()
                if not valid_series.empty:
                    st.metric(label=f"최근 {curr}", value=f"{valid_series.iloc[-1]:,.2f} 원")
                    
        # 통계 지표 테이블
        stats_df = df.describe().T[['count', 'mean', 'std', 'min', 'max']]
        stats_df.columns = ['관측치 개수', '평균값', '표준편차(변동성)', '최솟값', '최댓값']
        st.dataframe(stats_df.style.format("{:,.2f}"))
        
        # 상관관계 분석
        st.header("🔗 2. 통화 간 통계적 상관관계 검증")
        corr_matrix = df[currencies].corr(method='pearson')
        st.dataframe(corr_matrix.style.format("{:.4f}"))
        
        # 종합 변동성 비교
        st.header("⚡ 3. 일일 변동률 종합 리스크 비교")
        recent_return = return_df_clean.tail(150)
        st.line_chart(recent_return, color=["#0055ff", "#ff007f", "#00aa55"])
        
        # 변동성 요약
        vol_summary = pd.DataFrame({
            '일일 변동성 (표준편차 %)' : return_df_clean.std(),
            '최대 당일 상승률 (%)' : return_df_clean.max(),
            '최대 당일 하락률 (%)' : return_df_clean.min()
        })
        highest_vol_curr = vol_summary['일일 변동성 (표준편차 %)'].idxmax()
        st.info(f"📝 **통계적 결론:** 현재 선택 기간 외환 시장에서 리스크(변동성)가 가장 높은 통화는 **{highest_vol_curr}**입니다.")

    # ==========================================
    # PAGE 2: 미국 달러
    # ==========================================
    elif page == "🇺🇸 미국 (원/달러)":
        st.title("🇺🇸 미국 달러 (USD) 대원화 환율 심층 분석")
        
        # 1. 추세 분석 그래프
        st.header("📈 환율 추세 및 이동평균선(MA) 분석")
        df_usd = pd.DataFrame(index=df.index)
        df_usd['실제 달러 환율'] = df['원/달러']
        df_usd['20일 이평선'] = df['원/달러'].rolling(window=20).mean()
        df_usd['60일 이평선'] = df['원/달러'].rolling(window=60).mean()
        st.line_chart(df_usd, color=["#003f5c", "#2f4b7c", "#a0c4ff"])
        
        # 2. 리스크/히스토그램 분석
        st.header("📊 일일 변동률 분포 (Histogram)")
        counts, bin_edges = np.histogram(return_df_clean['원/달러'], bins=30)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        hist_usd = pd.DataFrame({'원/달러 변동 빈도': counts}, index=np.round(bin_centers, 2))
        st.bar_chart(hist_usd, color=["#1f77b4"])
        
        # 3. 통계 지표 요약
        st.header("📋 달러 리스크 통계 지표")
        st.write(f"- **선택 기간 평균 환율:** {df['원/달러'].mean():,.2f} 원")
        st.write(f"- **일일 변동성 (표준편차):** {return_df_clean['원/달러'].std():.3f}%")

    # ==========================================
    # PAGE 3: 일본 엔화
    # ==========================================
    elif page == "🇯🇵 일본 (원/100엔)":
        st.title("🇯🇵 일본 엔 (JPY 100) 대원화 환율 심층 분석")
        
        # 1. 추세 분석 그래프
        st.header("📈 환율 추세 및 이동평균선(MA) 분석")
        df_jpy = pd.DataFrame(index=df.index)
        df_jpy['실제 엔화 환율'] = df['원/100엔']
        df_jpy['20일 이평선'] = df['원/100엔'].rolling(window=20).mean()
        df_jpy['60일 이평선'] = df['원/100엔'].rolling(window=60).mean()
        st.line_chart(df_jpy, color=["#f95d6a", "#ff7c43", "#ffa600"])
        
        # 2. 리스크/히스토그램 분석
        st.header("📊 일일 변동률 분포 (Histogram)")
        counts, bin_edges = np.histogram(return_df_clean['원/100엔'], bins=30)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        hist_jpy = pd.DataFrame({'원/100엔 변동 빈도': counts}, index=np.round(bin_centers, 2))
        st.bar_chart(hist_jpy, color=["#ff7f0e"])
        
        # 3. 통계 지표 요약
        st.header("📋 엔화 리스크 통계 지표")
        st.write(f"- **선택 기간 평균 환율:** {df['원/100엔'].mean():,.2f} 원")
        st.write(f"- **일일 변동성 (표준편차):** {return_df_clean['원/100엔'].std():.3f}%")

    # ==========================================
    # PAGE 4: 중국 위안화
    # ==========================================
    elif page == "🇨🇳 중국 (원/위안)":
        st.title("🇨🇳 중국 위안 (CNY) 대원화 환율 심층 분석")
        
        # 1. 추세 분석 그래프
        st.header("📈 환율 추세 및 이동평균선(MA) 분석")
        df_cny = pd.DataFrame(index=df.index)
        df_cny['실제 위안 환율'] = df['원/위안']
        df_cny['20일 이평선'] = df['원/위안'].rolling(window=20).mean()
        df_cny['60일 이평선'] = df['원/위안'].rolling(window=60).mean()
        st.line_chart(df_cny, color=["#107c41", "#1f9e55", "#7bcd9b"])
        
        # 2. 리스크/히스토그램 분석
        st.header("📊 일일 변동률 분포 (Histogram)")
        counts, bin_edges = np.histogram(return_df_clean['원/위안'], bins=30)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        hist_cny = pd.DataFrame({'원/위안 변동 빈도': counts}, index=np.round(bin_centers, 2))
        st.bar_chart(hist_cny, color=["#2ca02c"])
        
        # 3. 통계 지표 요약
        st.header("📋 위안화 리스크 통계 지표")
        st.write(f"- **선택 기간 평균 환율:** {df['원/위안'].mean():,.2f} 원")
        st.write(f"- **일일 변동성 (표준편차):** {return_df_clean['원/위안'].std():.3f}%")
