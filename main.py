import streamlit as st
import pandas as pd
import numpy as np
import os

# 1. 웹앱 제목 및 서론
st.set_page_config(page_title="원화 환율 변동 추이 분석", layout="wide")
st.title("📈 주요국 통화의 대원화 환율 변동 추이 및 통계적 분석")
st.markdown("""
본 웹앱은 제공된 환율 데이터를 바탕으로 주요국 통화(미국 달러, 일본 엔, 중국 위안)의 대원화 환율 추이를 통계적으로 분석한 탐구 보고서 양식의 대시보드입니다.
""")

# 2. 데이터 업로드 및 자동 로드 기능 (CSV와 Excel 모두 지원)
st.sidebar.header("📁 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("주요국 통화 파일을 업로드하세요 (CSV 또는 엑셀 모두 가능)", type=["csv", "xlsx"])

@st.cache_data
def load_data(file_source, is_excel=False):
    # 엑셀 파일일 경우와 CSV 파일일 경우를 나누어 로드
    if is_excel:
        df = pd.read_excel(file_source, skiprows=8, names=['날짜', '원/달러', '원/100엔', '원/위안'])
    else:
        df = pd.read_csv(file_source, skiprows=8, names=['날짜', '원/달러', '원/100엔', '원/위안'])
    
    # 날짜 데이터 변환 및 인덱스 설정
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
    df = df.dropna(subset=['날짜']).sort_values('날짜')
    
    # 숫자형 데이터 변환
    for col in ['원/달러', '원/100엔', '원/위안']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return df

# 기본 파일 이름 정의들
FILE_NAME_CSV = "주요국 통화의 대원화 환율.xlsx - Sheet1.csv"
FILE_NAME_XLSX = "주요국 통화의 대원화 환율.xlsx"

df_raw = None

# 1순위: 사용자가 직접 웹 화면에 업로드했을 때
if uploaded_file is not None:
    is_excel = uploaded_file.name.endswith('.xlsx')
    df_raw = load_data(uploaded_file, is_excel=is_excel)
# 2순위: 깃허브 서버 내에 CSV 파일이 존재할 때
elif os.path.exists(FILE_NAME_CSV):
    df_raw = load_data(FILE_NAME_CSV, is_excel=False)
# 3순위: 깃허브 서버 내에 진짜 엑셀 파일이 존재할 때
elif os.path.exists(FILE_NAME_XLSX):
    df_raw = load_data(FILE_NAME_XLSX, is_excel=True)
else:
    st.warning("⚠️ 데이터 파일을 찾을 수 없습니다. 왼쪽 사이드바에서 엑셀(.xlsx) 또는 CSV 파일을 업로드해 주세요.")

# 데이터가 성공적으로 로드된 경우에만 아래 분석 코드가 실행됩니다.
if df_raw is not None:
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
        
        # 필터링된 데이터 생성
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
        st.header("📈 2. 환율 추세 및 이동평균선(MA) 분석")
        selected_curr = st.selectbox("분석할 통화를 선택하세요:", currencies)
        
        plot_df = pd.DataFrame(index=df.index)
        plot_df['실제 환율'] = df[selected_curr]
        plot_df['20일 이동평균'] = df[selected_curr].rolling(window=20).mean()
        plot_df['60일 이동평균'] = df[selected_curr].rolling(window=60).mean()
        
        st.line_chart(plot_df)

        # 6. 본문 - [연구 3] 통화 간 통계적 상관관계 분석
        st.header("🔗 3. 통화 간 상관관계 및 연동성 검증")
        corr_matrix = df[currencies].corr(method='pearson')
        st.dataframe(corr_matrix.style.background_gradient(cmap='coolwarm').format("{:.4f}"))

        # 7. 본문 - [연구 4] 일일 수익률 분포 및 변동성 분석
        st.header("⚡ 4. 환율 일일 변동률(수익률) 및 위험도 분석")
        return_df = df[currencies].pct_change() * 100
        
        st.subheader("📅 최근 일일 변동률 추이 (%)")
        st.bar_chart(return_df.tail(100))
        
        st.subheader("📊 변동성 지표 요약")
        vol_summary = pd.DataFrame({
            '일일 변동성 (표준편차 %)' : return_df.std(),
            '최대 상승률 (%)' : return_df.max(),
            '최대 하락률 (%)' : return_df.min()
        })
        st.dataframe(vol_summary.style.format("{:.3f}%"))

    except Exception as e:
        st.error(f"데이터 분석 중 오류가 발생했습니다. 파일 형식이 올바른지 확인해 주세요. 오류 내용: {e}")
