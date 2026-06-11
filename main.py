import streamlit as st
import pandas as pd
import numpy as np
import os

# 1. 웹앱 제목 및 서론
st.set_page_config(page_title="원화 환율 변동 추이 분석", layout="wide")
st.title("📈 주요국 통화의 대원화 환율 변동 추이 및 통계적 분석")
st.markdown("""
본 웹앱은 제공된 환율 데이터를 바탕으로 주요국 통화(미국 달러, 일본 엔, 중국 위안)의 대원화 환율 추이를 통계적으로 분석한 탐구 보고서 양식의 대시보드입니다.
별도의 라이브러리 없이 스트림릿 기본 기능만을 활용하여 작성되었습니다.
""")

# 2. 데이터 업로드 및 자동 로드 기능
st.sidebar.header("📁 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("주요국 통화 csv 파일을 업로드하세요", type=["csv"])

@st.cache_data
def load_data(file_source):
    # 앞선 주석 및 메타데이터 행(상위 8개 행)을 제외하고 데이터프레임 로드
    df = pd.read_csv(file_source, skiprows=8, names=['날짜', '원/달러', '원/100엔', '원/위안'])
    
    # 날짜 데이터 변환 및 인덱스 설정
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
    df = df.dropna(subset=['날짜']) # 날짜가 없는 행 제거
    df = df.sort_values('날짜')
    
    # 숫자형 데이터 변환
    for col in ['원/달러', '원/100엔', '원/위안']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return df

# 파일 이름 정의
FILE_NAME = "주요국 통화의 대원화 환율.xlsx - Sheet1.csv"

# 파일을 읽어오는 로직 (업로드된 파일 우선, 없으면 서버 내 파일 확인)
df_raw = None
if uploaded_file is not None:
    df_raw = load_data(uploaded_file)
elif os.path.exists(FILE_NAME):
    df_raw = load_data(FILE_NAME)
else:
    st.warning("⚠️ 데이터 파일을 찾을 수 없습니다. 왼쪽 사이드바에서 CSV 파일을 업로드하거나, GitHub 저장소에 파일을 함께 올려주세요.")

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
            value=(max_date - pd.Timedelta(days=365*2), max_date) # 기본값 최근 2년
        )
        
        # 필터링된 데이터 생성
        df = df_raw[(df_raw['날짜'] >= start_date) & (df_raw['날짜'] <= end_date)].copy()
        df.set_index('날짜', inplace=True)

        # 4. 본문 - [연구 1] 데이터 개요 및 기술 통계 (Descriptive Statistics)
        st.header("📋 1. 데이터 개요 및 기술 통계 분석")
        st.markdown("선택한 기간 동안의 기초 통계량을 통해 각 통화의 평균적인 수준과 극단치, 분포의 흩어진 정도를 파악합니다.")
        
        # 최근 환율 및 통계량 요약
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

        # 통계적 요약 테이블
        st.subheader("📊 주요 통계 지표")
        stats_df = df.describe().T[['count', 'mean', 'std', 'min', 'max']]
        stats_df.columns = ['관측치 개수', '평균값', '표준편차(변동성)', '최솟값', '최댓값']
        st.dataframe(stats_df.style.format("{:,.2f}"))
        
        st.caption("💡 **통계적 해석:** 표준편차가 클수록 해당 통화의 대원화 가치 변동성(위험도)이 높음을 의미합니다.")

        # 5. 본문 - [연구 2] 환율 변동 추이 및 이동평균선 분석
        st.header("📈 2. 환율 추세 및 이동평균선(MA) 분석")
        st.markdown("통계적 노이즈를 제거하고 장기적인 추세를 확인하기 위해 **20일, 60일 이동평균선(Moving Average)**을 적용한 시각화입니다.")
        
        selected_curr = st.selectbox("분석할 통화를 선택하세요:", currencies)
        
        # 이동평균 데이터 생성
        plot_df = pd.DataFrame(index=df.index)
        plot_df['실제 환율'] = df[selected_curr]
        plot_df['20일 이동평균'] = df[selected_curr].rolling(window=20).mean()
        plot_df['60일 이동평균'] = df[selected_curr].rolling(window=60).mean()
        
        # 스트림릿 기본 라인 차트 시각화
        st.line_chart(plot_df)
        st.markdown(f"**골든크로스/데드크로스 분석:** 20일 이평선이 60일 이평선을 상향 돌파하면 단기 상승 추세, 하향 돌파하면 단기 하락 추세로 해석할 수 있습니다.")

        # 6. 본문 - [연구 3] 통화 간 통계적 상관관계 분석 (Correlation Analysis)
        st.header("🔗 3. 통화 간 상관관계 및 연동성 검증")
        st.markdown("피어슨 상관계수(Pearson Correlation Coefficient)를 활용하여 원화 대비 주요국 통화들이 서로 얼마나 같은 방향으로 움직이는지 통계적으로 증명합니다.")
        
        corr_matrix = df[currencies].corr(method='pearson')
        
        st.subheader("📉 피어슨 상관계수 행렬")
        st.dataframe(corr_matrix.style.background_gradient(cmap='coolwarm').format("{:.4f}"))
        
        st.markdown("""
        * **상관계수 해석 기준:**
            * `+0.7 이상`: 강한 양의 상관관계 (두 통화가 원화 대비 같이 가치가 상승/하락함)
            * `0.3 ~ 0.7`: 뚜렷한 양의 상관관계
            * `-0.3 ~ +0.3`: 선형적 연동성 낮음
            * `-0.3 이하`: 음의 상관관계 (한 통화가 오르면 다른 통화는 떨어짐)
        """)

        # 7. 본문 - [연구 4] 일일 수익률 분포 및 변동성 분석
        st.header("⚡ 4. 환율 일일 변동률(수익률) 및 위험도 분석")
        st.markdown("환율의 절대적인 수치 외에, **전일 대비 일일 변동률**을 통해 통계적 왜도와 리스크를 측정합니다.")
        
        # 일일 변동률 계산 (%)
        return_df = df[currencies].pct_change() * 100
        
        # 스트림릿 기본 바 차트를 이용한 최근 변동 추이
        st.subheader("📅 최근 일일 변동률 추이 (%)")
        st.bar_chart(return_df.tail(100)) # 시인성을 위해 최근 100거래일 배치
        
        # 변동성 통계 증명
        st.subheader("📊 변동성 지표 요약")
        vol_summary = pd.DataFrame({
            '일일 변동성 (표준편차 %)' : return_df.std(),
            '최대 상승률 (%)' : return_df.max(),
            '최대 하락률 (%)' : return_df.min()
        })
        st.dataframe(vol_summary.style.format("{:.3f}%"))
        st.markdown("💡 **결론:** '일일 변동성(표준편차)'이 가장 높은 통화가 투자 및 외환 관리 측면에서 가장 위험도가 높은(Volatility) 자산임을 통계적으로 증명합니다.")

    except Exception as e:
        st.error(f"데이터 분석 중 오류가 발생했습니다: {e}")
