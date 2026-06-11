# 기존 코드의 2번 영역을 아래처럼 수정해 보세요.

st.sidebar.header("📁 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("주요국 통화 csv 파일을 업로드하세요", type=["csv"])

@st.cache_data
def load_data(file_source):
    # 상위 8개 행 스킵 및 전처리
    df = pd.read_csv(file_source, skiprows=8, names=['날짜', '원/달러', '원/100엔', '원/위안'])
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
    df = df.dropna(subset=['날짜']).sort_values('날짜')
    for col in ['원/달러', '원/100엔', '원/위안']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

# 파일이 업로드되었거나, 서버에 파일이 존재하는 경우 구동
import os
FILE_NAME = "주요국 통화의 대원화 환율.xlsx - Sheet1.csv"

if uploaded_file is not None:
    df_raw = load_data(uploaded_file)
elif os.path.exists(FILE_NAME):
    df_raw = load_data(FILE_NAME)
else:
    df_raw = None
    st.warning("⚠️ 데이터 파일을 찾을 수 없습니다. 왼쪽 사이드바에서 CSV 파일을 업로드하거나, GitHub 저장소에 파일을 올려주세요.")

if df_raw is not None:
    # 이 아래부터는 기존 [3. 사이드바 ~] 코드가 그대로 들어가면 됩니다.
