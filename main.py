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
        "분석 및 탐구 단계를 선택하세요",
        ["🏠 홈 (종합 분석)", "🔮 미래 환율 예측 탐구", "🇺🇸 미국 (원/달러)", "🇯🇵 일본 (원/100엔)", "🇨🇳 중국 (원/위안)"]
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
    
    # 변동률 데이터 선행 계산
    return_df = df[currencies].pct_change() * 100
    return_df_clean = return_df.dropna()
    
    # ==========================================
    # PAGE 1: 홈 (종합 분석)
    # ==========================================
    if page == "🏠 홈 (종합 분석)":
        st.title("📈 주요국 통화의 대원화 환율 변동 추이 및 통계적 분석")
        st.markdown("본 대시보드는 미국 달러, 일본 엔, 중국 위안화의 대원화 환율 데이터를 기반으로 한 통계 탐구 보고서입니다.")
        
        st.header("📋 1. 최근 환율 및 기술 통계 개요")
        cols = st.columns(3)
        for i, curr in enumerate(currencies):
            with cols[i]:
                valid_series = df[curr].dropna()
                if not valid_series.empty:
                    st.metric(label=f"최근 {curr}", value=f"{valid_series.iloc[-1]:,.2f} 원")
                    
        stats_df = df.describe().T[['count', 'mean', 'std', 'min', 'max']]
        stats_df.columns = ['관측치 개수', '평균값', '표준편차(변동성)', '최솟값', '최댓값']
        st.dataframe(stats_df.style.format("{:,.2f}"))
        
        st.header("🔗 2. 통화 간 통계적 상관관계 검증")
        corr_matrix = df[currencies].corr(method='pearson')
        st.dataframe(corr_matrix.style.format("{:.4f}"))
        
        st.header("⚡ 3. 일일 변동률 종합 리스크 비교")
        st.line_chart(return_df_clean.tail(150), color=["#0055ff", "#ff007f", "#00aa55"])

    # ==========================================
    # 🔮 NEW PAGE: 미래 환율 예측 탐구
    # ==========================================
    elif page == "🔮 미래 환율 예측 탐구":
        st.title("🔮 환율은 점점 오르고 있을까? 추세 분석 및 미래 예측")
        st.markdown("""
        본 페이지에서는 **"선택한 기간 동안 환율이 통계적으로 상승세인가, 하락세인가?"**라는 의문을 검증합니다.
        통계학의 **선형 회귀 분석(Linear Regression)** 알고리즘을 이용해 과거 데이터의 기울기를 구하고, 이를 바탕으로 앞으로 **30거래일 뒤의 미래 환율**을 예측합니다.
        """)
        
        selected_curr = st.selectbox("예측 모델을 구동할 통화를 선택하세요", currencies)
        
        # 선형 회귀 계산을 위한 데이터 준비
        y_data = df[selected_curr].dropna()
        if len(y_data) > 10:
            # 날짜를 연속된 정수(0, 1, 2...) 형태로 변환하여 독립변수 X 생성
            x_data = np.arange(len(y_data))
            
            # 1차 방정식 기울기(m)와 절편(c) 계산 (y = mx + c)
            m, c = np.polyfit(x_data, y_data, 1)
            
            # 추세선 생성
            trend_line = m * x_data + c
            
            # 미래 30일 예측 데이터 생성
            future_x = np.arange(len(y_data), len(y_data) + 30)
            future_y = m * future_x + c
            
            # 시각화용 데이터프레임 조립
            total_index = list(y_data.index) + [y_data.index[-1] + pd.Timedelta(days=i) for i in range(1, 31)]
            
            plot_df = pd.DataFrame(index=total_index)
            plot_df['과거 실제 환율'] = pd.Series(y_data.values, index=y_data.index)
            plot_df['과거 통계 추세선'] = pd.Series(trend_line, index=y_data.index)
            plot_df['미래 30일 예측 환율'] = pd.Series(future_y, index=total_index[-30:])
            
            # 차트 그리기
            st.subheader(f"📊 {selected_curr} 데이터 분석 및 선형 예측 그래프")
            st.line_chart(plot_df, color=["#1f77b4", "#ff7f0e", "#d62728"])
            
            # 통계 기반 결론 및 판단
            st.header("📝 통계적 추세 진단 및 미래 값 예측")
            
            # 현재 환율과 30일 뒤 예측값 비교
            current_val = y_data.iloc[-1]
            future_val = future_y[-1]
            diff_val = future_val - current_val
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("현재 환율", f"{current_val:,.2f} 원")
            with col2:
                st.metric("30거래일 뒤 예측 환율", f"{future_val:,.2f} 원")
            with col3:
                st.metric("예측 변동폭", f"{diff_val:+,.2f} 원")
                
            # 기울기에 따른 상승/하락 판정
            if m > 0:
                st.success(f"📈 **진단 결론:** 선택한 기간 동안 {selected_curr}은(는) 하루 평균 **{m:.4f}원씩 상승**하는 통계적 흐름을 보이고 있습니다. 데이터 분석 결과, 단기 미래에도 원화 대비 **상승세(원화 약세)**가 지속될 가능성이 높습니다.")
            else:
                st.warning(f"📉 **진단 결론:** 선택한 기간 동안 {selected_curr}은(는) 하루 평균 **{abs(m):.4f}원씩 하락**하는 통계적 흐름을 보이고 있습니다. 데이터 분석 결과, 단기 미래에도 원화 대비 **하락세(원화 강세)**가 지속될 가능성이 높습니다.")
                
            st.markdown("""
            > ⚠️ **학술적 유의사항:** 본 예측은 과거 지정 기간의 데이터를 선형 직선으로 연장한 **통계학적 추세 예측**입니다. 실제 외환 시장은 각국의 통화 정책, 금리 차이, 지정학적 리스크 등 예측 불가능한 변수가 복합적으로 작용하므로 실제 수치와 차이가 발생할 수 있으며 탐구 분석용으로 참고해야 합니다.
            """)
        else:
            st.error("데이터의 개수가 너무 적어 예측 모델을 구동할 수 없습니다. 분석 기간을 더 넓혀 주세요.")

    # ==========================================
    # PAGE 3: 미국 달러
    # ==========================================
    elif page == "🇺🇸 미국 (원/달러)":
        st.title("🇺🇸 미국 달러 (USD) 대원화 환율 심층 분석")
        st.header("📈 환율 추세 및 이동평균선(MA) 분석")
        df_usd = pd.DataFrame(index=df.index)
        df_usd['실제 달러 환율'] = df['원/달러']
        df_usd['20일 이평선'] = df['원/달러'].rolling(window=20).mean()
        df_usd['60일 이평선'] = df['원/달러'].rolling(window=60).mean()
        st.line_chart(df_usd, color=["#003f5c", "#2f4b7c", "#a0c4ff"])
        
        st.header("📊 일일 변동률 분포 (Histogram)")
        counts, bin_edges = np.histogram(return_df_clean['원/달러'], bins=30)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        hist_usd = pd.DataFrame({'원/달러 변동 빈도': counts}, index=np.round(bin_centers, 2))
        st.bar_chart(hist_usd, color=["#1f77b4"])

    # ==========================================
    # PAGE 4: 일본 엔화
    # ==========================================
    elif page == "🇯🇵 일본 (원/100엔)":
        st.title("🇯🇵 일본 엔 (JPY 100) 대원화 환율 심층 분석")
        st.header("📈 환율 추세 및 이동평균선(MA) 분석")
        df_jpy = pd.DataFrame(index=df.index)
        df_jpy['실제 엔화 환율'] = df['원/100엔']
        df_jpy['20일 이평선'] = df['원/100엔'].rolling(window=20).mean()
        df_jpy['60일 이평선'] = df['원/100엔'].rolling(window=60).mean()
        st.line_chart(df_jpy, color=["#f95d6a", "#ff7c43", "#ffa600"])
        
        st.header("📊 일일 변동률 분포 (Histogram)")
        counts, bin_edges = np.histogram(return_df_clean['원/100엔'], bins=30)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        hist_jpy = pd.DataFrame({'원/100엔 변동 빈도': counts}, index=np.round(bin_centers, 2))
        st.bar_chart(hist_jpy, color=["#ff7f0e"])

    # ==========================================
    # PAGE 5: 중국 위안화
    # ==========================================
    elif page == "🇨🇳 중국 (원/위안)":
        st.title("🇨🇳 중국 위안 (CNY) 대원화 환율 심층 분석")
        st.header("📈 환율 추세 및 이동평균선(MA) 분석")
        df_cny = pd.DataFrame(index=df.index)
        df_cny['실제 위안 환율'] = df['원/위안']
        df_cny['20일 이평선'] = df['원/위안'].rolling(window=20).mean()
        df_cny['60일 이평선'] = df['원/위안'].rolling(window=60).mean()
        st.line_chart(df_cny, color=["#107c41", "#1f9e55", "#7bcd9b"])
        
        st.header("📊 일일 변동률 분포 (Histogram)")
        counts, bin_edges = np.histogram(return_df_clean['원/위안'], bins=30)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        hist_cny = pd.DataFrame({'원/위안 변동 빈도': counts}, index=np.round(bin_centers, 2))
        st.bar_chart(hist_cny, color=["#2ca02c"])
