import streamlit as st
import pandas as pd
import numpy as np

# 1. 웹앱 제목 및 서론
st.set_page_config(page_title="원화 환율 변동 추이 분석", layout="wide")
st.title("📈 주요국 통화의 대원화 환율 변동 추이 및 통계적 분석")
st.markdown("""
본 웹앱은 제공된 환율 데이터를 바탕으로 주요국 통화(미국 달러, 일본 엔, 중국 위안)의 대원화 환율 추이를 통계적으로 분석한 탐구 보고서 양식의 대시보드입니다.
""")

# 💡 [핵심 수정] 사용자가 파일 업로드를 안 해도 깃허브에서 직접 가져오도록 설정
# 본인의 깃허브 ID와 저장소명(Repository 이름)으로 주소를 바꾸면 영구히 작동합니다.
# 예시: "https://raw.githubusercontent.com/깃허브ID/저장소명/main/주요국%20통화의%20대원화%20환율.xlsx%20-%20Sheet1.csv"
DATA_URL = "https://raw.githubusercontent.com/dataaa11/dataaa11/main/%EC%A3%BC%EC%9A%94%EA%B5%AD%20%ED%86%B5%ED%99%94%EC%9D%98%20%EB%8C%80%EC%9B%90%ED%99%94%20%ED%99%98%EC%9C%A8.xlsx%20-%20Sheet1.csv"

@st.cache_data
def load_data_from_url(url):
    # 한글 인코딩 오류 방지
    encodings = ['utf-8', 'cp949', 'euc-kr', 'utf-8-sig']
    df = None
    for enc in encodings:
        try:
            df = pd.read_csv(url, skiprows=8, names=['날짜', '원/달러', '원/100엔', '원/위안'], encoding=enc)
            break
        except:
            continue
    
    if df is None:
        raise ValueError("데이터 로드 실패")
        
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
    df = df.dropna(subset=['날짜']).sort_values('날짜')
    for col in ['원/달러', '원/100엔', '원/위안']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

# 사용자가 아무것도 안 해도 링크에서 자동으로 가져옴
try:
    df_raw = load_data_from_url(DATA_URL)
except Exception as e:
    st.error(f"데이터를 불러오지 못했습니다. URL주소나 깃허브에 파일이 있는지 확인해주세요. 에러: {e}")
    df_raw = None

# 데이터가 로드되면 바로 화면 출력
if df_raw is not None:
    # --- 이 아래부터는 기존 분석 코드와 완전히 동일합니다 ---
    try:
        # 3. 사이드바 - 분석 기간 및 통화 선택
        st.sidebar.header("🔍 분석 설정")
        
        min_date = df_raw['날짜'].min().to_pydatetime()
        max_date = df_raw['날짜'].max().to_pydatetime()
        
        start_date, end_date = st.sidebar.slider(
            "분석 기간 선택",
            min_value=min_date,
            max_value=max_date,
            value=(max_date - pd.Timedelta(days=365*2), max_date)
        )
        
        df = df_raw[(df_raw['날짜'] >= start_date) & (df_raw['날짜'] <= end_date)].copy()
        df.set_index('날짜', inplace=True)

        # 4. 본문 - [연구 1] 데이터 개요 및 기술 통계
        st.header("📋 1. 데이터 개요 및 기술 통계 분석")
        st.markdown("선택한 기간 동안의 기초 통계량을 통해 각 통화의 평균적인 수준과 분포의 흩어진 정도를 파악합니다.")
        
        cols = st.columns(3)
        currencies = ['원/달러', '원/100엔', '원/위안']
        
        for i, curr in enumerate(currencies):
            with cols[i]:
                valid_series = df[curr].dropna()
                if not valid_series.empty:
                    latest_val = valid_series.iloc[-1]
                    st.metric(label=f"최근 {curr}", value=f"{latest_val:,.2f} 원")
                else:
                    st.metric(label=f"최근 {curr}", value="데이터 없음")

        st.subheader("📊 주요 통계 지표")
        stats_df = df.describe().T[['count', 'mean', 'std', 'min', 'max']]
        stats_df.columns = ['관측치 개수', '평균값', '표준편차(변동성)', '최솟값', '최댓값']
        st.dataframe(stats_df.style.format("{:,.2f}"))

        # 5. 본문 - [연구 2] 환율 변동 추이 및 이동평균선 분석
        st.header("📈 2. 통화별 환율 추세 및 이동평균선(MA) 분석")
        tab1, tab2, tab3 = st.tabs(["🇺🇸 원/달러", "🇯🇵 원/100엔", "🇨🇳 원/위안"])
        
        with tab1:
            st.subheader("미국 달러 (USD) 추세 분석")
            df_usd = pd.DataFrame(index=df.index)
            df_usd['실제 달러 환율'] = df['원/달러']
            df_usd['20일 이평선'] = df['원/달러'].rolling(window=20).mean()
            df_usd['60일 이평선'] = df['원/달러'].rolling(window=60).mean()
            st.line_chart(df_usd, color=["#003f5c", "#2f4b7c", "#a0c4ff"])
            
        with tab2:
            st.subheader("일본 엔 (JPY 100) 추세 분석")
            df_jpy = pd.DataFrame(index=df.index)
            df_jpy['실제 엔화 환율'] = df['원/100엔']
            df_jpy['20일 이평선'] = df['원/100엔'].rolling(window=20).mean()
            df_jpy['60일 이평선'] = df['원/100엔'].rolling(window=60).mean()
            st.line_chart(df_jpy, color=["#f95d6a", "#ff7c43", "#ffa600"])
            
        with tab3:
            st.subheader("중국 위안 (CNY) 추세 분석")
            df_cny = pd.DataFrame(index=df.index)
            df_cny['실제 위안 환율'] = df['원/위안']
            df_cny['20일 이평선'] = df['원/위안'].rolling(window=20).mean()
            df_cny['60일 이평선'] = df['원/위안'].rolling(window=60).mean()
            st.line_chart(df_cny, color=["#107c41", "#1f9e55", "#7bcd9b"])

        # 6. 본문 - [연구 3] 통화 간 통계적 상관관계 분석
        st.header("🔗 3. 통화 간 상관관계 및 연동성 검증")
        corr_matrix = df[currencies].corr(method='pearson')
        st.dataframe(corr_matrix.style.format("{:.4f}"))

        # 7. 본문 - [연구 4] 일일 수익률 분포 및 변동성 분석
        st.header("⚡ 4. 환율 일일 변동률 및 통계적 위험도 분석")
        return_df = df[currencies].pct_change() * 100
        return_df_clean = return_df.dropna()
        recent_return = return_df_clean.tail(150)
        
        v_tab1, v_tab2 = st.tabs(["📉 시계열 변동률 추이 비교", "📊 변동성 분포(히스토그램) 분석"])
        
        with v_tab1:
            st.subheader("최근 150거래일 일일 변동률 추이 (%)")
            st.line_chart(recent_return, color=["#0055ff", "#ff007f", "#00aa55"])
            
        with v_tab2:
            st.subheader("📊 통화별 변동률 분포 분석 (Histogram)")
            hist_data = pd.DataFrame()
            for curr in currencies:
                counts, bin_edges = np.histogram(return_df_clean[curr], bins=30)
                bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                hist_data[f'{curr} 변동 빈도'] = pd.Series(counts, index=np.round(bin_centers, 2))
            
            sub_tab0, sub_tab1, sub_tab2, sub_tab3 = st.tabs([
                "🔄 종합 교차 비교", "🇺🇸 미국 달러 분포", "🇯🇵 일본 엔 분포", "🇨🇳 중국 위안 분포"
            ])
            
            with sub_tab0:
                st.bar_chart(hist_data, color=["#1f77b4", "#ff7f0e", "#2ca02c"])
            with sub_tab1:
                st.bar_chart(hist_data[[f'원/달러 변동 빈도']], color=["#1f77b4"])
            with sub_tab2:
                st.bar_chart(hist_data[[f'원/100엔 변동 빈도']], color=["#ff7f0e"])
            with sub_tab3:
                st.bar_chart(hist_data[[f'원/위안 변동 빈도']], color=["#2ca02c"])

        st.subheader("📊 리스크 평가 지표 요약")
        vol_summary = pd.DataFrame({
            '일일 변동성 (표준편차 %)' : return_df_clean.std(),
            '최대 당일 상승률 (%)' : return_df_clean.max(),
            '최대 당일 하락률 (%)' : return_df_clean.min()
        })
        st.dataframe(vol_summary.style.format("{:.3f}%"))
        
        highest_vol_curr = vol_summary['일일 변동성 (표준편차 %)'].idxmax()
        highest_vol_val = vol_summary['일일 변동성 (표준편차 %)'].max()
        
        st.info(f"""
        📝 **통계적 분석 결론:** 선택하신 기간 동안 대원화 환율 시장에서 가장 위험도(변동성)가 높은 통화는 **{highest_vol_curr}**(표준편차 {highest_vol_val:.3f}%)인 것으로 통계적으로 증명되었습니다. 
        """)

    except Exception as e:
        st.error(f"오류 발생: {e}")
