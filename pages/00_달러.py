import streamlit as st
import pandas as pd
import numpy as np
import os

st.set_page_config(page_title="미국 (원/달러) 분석", layout="wide")

@st.cache_data
def load_data():
    file_path = "주요국 통화의 대원화 환율.csv"
    if not os.path.exists(file_path): return None
    for enc in ['utf-8', 'cp949', 'euc-kr', 'utf-8-sig']:
        try:
            df = pd.read_csv(file_path, skiprows=8, names=['날짜', '원/달러', '원/100엔', '원/위안'], encoding=enc)
            df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
            df = df.dropna(subset=['날짜']).sort_values('날짜')
            df['원/달러'] = pd.to_numeric(df['원/달러'], errors='coerce')
            return df[['날짜', '원/달러']].dropna()
        except: continue
    return None

df_raw = load_data()

if df_raw is not None:
    st.title("🇺🇸 미국 달러 (USD) 환율의 변화와 예측")
    
    # 기간 설정
    min_date, max_date = df_raw['날짜'].min().to_pydatetime(), df_raw['날짜'].max().to_pydatetime()
    start_date, end_date = st.sidebar.slider("분석 기간 선택", min_value=min_date, max_value=max_date, value=(max_date - pd.Timedelta(days=365*2), max_date))
    df = df_raw[(df_raw['날짜'] >= start_date) & (df_raw['날짜'] <= end_date)].copy()
    df.set_index('날짜', inplace=True)
    
    # 1. 추세 분석
    st.header("📈 환율 추세 변화 및 이동평균선(MA) 분석")
    df_usd = pd.DataFrame(index=df.index)
    df_usd['실제 달러 환율 변화'] = df['원/달러']
    df_usd['20일 이평선'] = df['원/달러'].rolling(window=20).mean()
    df_usd['60일 이평선'] = df['원/달러'].rolling(window=60).mean()
    st.line_chart(df_usd, color=["#003f5c", "#2f4b7c", "#a0c4ff"])
    
    # 2. 2030 장기 예측 (GBM)
    st.header("🔮 2030년 장기 변화 예측 (기하 브라운 운동 모델)")
    current_val = df['원/달러'].iloc[-1]
    last_date = df.index[-1]
    target_date = pd.to_datetime("2030-12-31")
    days_to_predict = int(np.busday_count(last_date.date(), target_date.date()))
    
    if days_to_predict > 0:
        returns = df['원/달러'].pct_change().dropna()
        mu, sigma = returns.mean(), returns.std()
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), end=target_date, freq='B')[:days_to_predict]
        actual_length = len(future_dates)
        
        np.random.seed(42)
        simulations = np.zeros((actual_length, 30))
        for i in range(30):
            rand_shocks = np.random.normal(0, 1, actual_length)
            cum_shocks = np.cumsum(rand_shocks)
            time_steps = np.arange(1, actual_length + 1)
            simulations[:, i] = current_val * np.exp((mu - 0.5 * (sigma**2)) * time_steps + sigma * np.sqrt(time_steps) * (cum_shocks / np.sqrt(time_steps)))
            
        mean_path = np.mean(simulations, axis=1)
        upper_path = np.percentile(simulations, 90, axis=1)
        lower_path = np.percentile(simulations, 10, axis=1)
        
        plot_df = pd.DataFrame(index=list(df.index) + list(future_dates))
        plot_df['과거 실제 환율 변화'] = pd.Series(df['원/달러'].values, index=df.index)
        plot_df['2030 평균 추세 예측선'] = pd.Series(mean_path, index=future_dates)
        plot_df['상한 변화 경계 (폭등 시나리오)'] = pd.Series(upper_path, index=future_dates)
        plot_df['하한 변화 경계 (폭락 시나리오)'] = pd.Series(lower_path, index=future_dates)
        st.line_chart(plot_df, color=["#1f77b4", "#ff7f0e", "#d62728", "#2ca02c"])
        
        st.metric("2030년 평균 예측값", f"{mean_path[-1]:,.2f} 원", f"{mean_path[-1] - current_val:+,.2f} 원")

    # 3. 히스토그램
    st.header("📊 일일 환율 변화 폭 분포 (Histogram)")
    counts, bin_edges = np.histogram(df['원/달러'].pct_change().dropna() * 100, bins=30)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    hist_df = pd.DataFrame({'원/달러 변화 빈도': counts}, index=np.round(bin_centers, 2))
    st.bar_chart(hist_df, color=["#1f77b4"])
