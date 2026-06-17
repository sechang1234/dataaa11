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
        ["🏠 홈 (종합 분석)", "🔮 2030년 장기 환율 예측", "🇺🇸 미국 (원/달러)", "🇯🇵 일본 (원/100엔)", "🇨🇳 중국 (원/위안)"]
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
    return_df = df[currencies].pct_change()
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
        st.line_chart(return_df_clean.tail(150) * 100, color=["#0055ff", "#ff007f", "#00aa55"])

    # ==========================================
    # 🔮 NEW PAGE: 2030년 장기 환율 예측 (GBM 모델)
    # ==========================================
    elif page == "🔮 2030년 장기 환율 예측":
        st.title("🔮 환율은 점점 오르고 있을까? 2030년 장기 시뮬레이션")
        st.markdown("""
        수년 이상의 장기 예측에서는 단순한 직선 추세선을 쓰면 비현실적인 수치가 나옵니다. 
        따라서 금융공학에서 자산 가격 예측에 활용하는 **기하 브라운 운동(Geometric Brownian Motion, GBM)** 모델을 적용합니다. 
        이 모델은 과거 데이터의 **평균 상승률(Drift)**과 **시장 위험도(Volatility)**를 추출하여, 변동성을 포함한 2030년까지의 미래 시나리오를 무작위로 수백 번 계산합니다.
        """)
        
        selected_curr = st.selectbox("시뮬레이션할 통화를 선택하세요", currencies)
        
        # 실제 데이터 준비
        y_data = df[selected_curr].dropna()
        current_val = y_data.iloc[-1]
        last_date = y_data.index[-1]
        
        # 2030년 12월 31일까지 남은 거래일 계산 (1년 대략 250거래일 가정)
        target_date = pd.to_datetime("2030-12-31")
        days_to_predict = int(np.busday_count(last_date.date(), target_date.date()))
        
        if days_to_predict <= 0:
            st.error("현재 데이터의 마지막 날짜가 이미 2030년 이후입니다.")
        elif len(y_data) > 20:
            # GBM 파라미터 추출 (일일 수익률 기반)
            returns = y_data.pct_change().dropna()
            mu = returns.mean()           # 일일 평균 성장률
            sigma = returns.std()         # 일일 변동성(위험도)
            
            # 미래 날짜 인덱스 생성
            future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), end=target_date, freq='B')[:days_to_predict]
            actual_length = len(future_dates)
            
            # 50번의 무작위 시나리오 생성 (몬테카를로 시뮬레이션)
            np.random.seed(42) # 결과 고정
            simulations = np.zeros((actual_length, 50))
            
            for i in range(50):
                # GBM 수식: S(t) = S(0) * exp((mu - 0.5*sigma^2)*t + sigma*W(t))
                rand_shocks = np.random.normal(0, 1, actual_length)
                cum_shocks = np.cumsum(rand_shocks)
                time_steps = np.arange(1, actual_length + 1)
                
                path = current_val * np.exp((mu - 0.5 * (sigma**2)) * time_steps + sigma * np.sqrt(time_steps) * (cum_shocks / np.sqrt(time_steps)))
                simulations[:, i] = path
                
            # 시나리오 요약 계산 (평균적 예측, 상위 위험 예측, 하위 위험 예측)
            mean_path = np.mean(simulations, axis=1)
            upper_path = np.percentile(simulations, 90, axis=1) # 상위 90% 시나리오 (폭등 시)
            lower_path = np.percentile(simulations, 10, axis=1) # 하위 10% 시나리오 (폭락 시)
            
            # 데이터프레임 시각화 구성
            total_index = list(y_data.index) + list(future_dates)
            plot_df = pd.DataFrame(index=total_index)
            plot_df['과거 실제 환율'] = pd.Series(y_data.values, index=y_data.index)
            plot_df['2030 평균 추세 예측'] = pd.Series(mean_path, index=future_dates)
            plot_df['최대 상승 시나리오 (위험 경계)'] = pd.Series(upper_path, index=future_dates)
            plot_df['최대 하락 시나리오 (안정 경계)'] = pd.Series(lower_path, index=future_dates)
            
            st.subheader(f"📊 {selected_curr} 2030년 장기 확률적 변동 범위 시뮬레이션")
            st.line_chart(plot_df, color=["#1f77b4", "#ff7f0e", "#d62728", "#2ca02c"])
            
            # 통계 리포트 출력
            st.header("📝 2030년 장기 트렌드 진단서")
            
            future_mean_val = mean_path[-1]
            future_upper_val = upper_path[-1]
            future_lower_val = lower_path[-1]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("2030년 중간값 예측", f"{future_mean_val:,.2f} 원", f"{future_mean_val - current_val:+,.2f} 원")
            with col2:
                st.metric("최대 폭등 시나리오", f"{future_upper_val:,.2f} 원")
            with col3:
                st.metric("최대 폭락 시나리오", f"{future_lower_val:,.2f} 원")
                
            # 텍스트 분석 자동 도출
            annual_mu = mu * 250 * 100 # 연환산 성장률
            if annual_mu > 0:
                st.success(f"📈 **장기 추세 진단:** 과거 데이터 분석 결과, {selected_curr}은(는) 연평균 약 **{annual_mu:.2f}%의 상승 동력**을 내포하고 있습니다. 통계적 중간값 기준으로 2030년 말 환율은 현재보다 상승한 **{future_mean_val:,.2f}원** 근처에서 형성될 확률이 높습니다.")
            else:
                st.warning(f"📉 **장기 추세 진단:** 과거 데이터 분석 결과, {selected_curr}은(는) 연평균 약 **{abs(annual_mu):.2f}%의 하락 동력**을 내포하고 있습니다. 통계적 중간값 기준으로 2030년 말 환율은 현재보다 하락한 **{future_mean_val:,.2f}원** 근처에서 형성될 확률이 높습니다.")
                
            st.info(f"💡 **보고서용 통계 팁:** 환율이 한 점으로 예측되지 않고 붉은 선과 초록 선 사이의 거리가 뒤로 갈수록 부채꼴 모양으로 넓어지는 이유는, 시간이 흐를수록 미래의 **불확실성(리스크 프리미엄)**이 누적되는 외환 시장의 실제 통계적 속성을 완벽히 반영했기 때문입니다.")
        else:
            st.error("데이터가 부족합니다.")

    # ==========================================
    # PAGE 3 ~ 5: 국가별 상세 페이지
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
