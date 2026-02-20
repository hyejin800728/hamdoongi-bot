import streamlit as st
import pandas as pd
import time
import hashlib
import hmac
import base64
import requests
import random

# --- [보안] Streamlit Secrets를 통해 API 키를 안전하게 불러옵니다 ---
NAVER_CLIENT_ID = st.secrets["NAVER_CLIENT_ID"]
NAVER_CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]
AD_ACCESS_KEY = st.secrets["AD_ACCESS_KEY"]
AD_SECRET_KEY = st.secrets["AD_SECRET_KEY"]
AD_CUSTOMER_ID = st.secrets["AD_CUSTOMER_ID"]

# --- 1. 네이버 API 인증 함수 ---
def get_header(method, uri, api_key, secret_key, customer_id):
    timestamp = str(int(time.time() * 1000))
    signature = hmac.new(secret_key.encode(), (timestamp + "." + method + "." + uri).encode(), hashlib.sha256).digest()
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": api_key,
        "X-Customer": str(customer_id),
        "X-Signature": base64.b64encode(signature).decode()
    }

# --- 2. 데이터 수집 함수 (띄어쓰기 방지 적용) ---
def fetch_all_keyword_data(target_kw):
    clean_kw = target_kw.replace(" ", "")
    uri = "/keywordstool"
    method = "GET"
    params = {"hintKeywords": clean_kw, "showDetail": "1"}
    headers = get_header(method, uri, AD_ACCESS_KEY, AD_SECRET_KEY, AD_CUSTOMER_ID)
    ad_res = requests.get("https://api.naver.com" + uri, params=params, headers=headers)
    res_json = ad_res.json()
    if 'keywordList' not in res_json: return []
    
    all_keywords = res_json['keywordList'][:15]
    results = []
    
    progress_text = st.empty()
    progress_bar = st.progress(0)
    for i, item in enumerate(all_keywords):
        kw = item['relKeyword']
        progress_text.text(f"🐹 햄둥이가 '{kw}' 분석 중... ({i+1}/{len(all_keywords)})")
        def clean_count(val):
            if isinstance(val, str) and '<' in val: return 10
            return int(val)
        search_vol = clean_count(item['monthlyPcQcCnt']) + clean_count(item['monthlyMobileQcCnt'])
        search_url = f"https://openapi.naver.com/v1/search/blog.json?query={kw}&display=1"
        search_headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        search_res = requests.get(search_url, headers=search_headers)
        doc_count = search_res.json().get('total', 0)
        comp_idx = round(doc_count / search_vol, 2) if search_vol > 0 else 0
        results.append({"키워드": kw, "월간 검색량": search_vol, "총 문서 수": doc_count, "경쟁 강도": comp_idx})
        progress_bar.progress((i + 1) / len(all_keywords))
        time.sleep(0.05)
    progress_text.empty()
    progress_bar.empty()
    return results

# --- 3. AI 제목 생성 함수 (랜덤 조합) ---
def generate_titles(keyword):
    styles = {
        "감성형": [f"✨ [공감] {keyword} 때문에 고민인 당신에게 건네는 따뜻한 위로", f"🌿 {keyword} 속에서 발견한 작은 행복, 우리 함께 나눠요"],
        "정보형": [f"📝 햄둥이가 직접 정리한 {keyword} 핵심 가이드", f"🔍 초보자도 1분 만에 이해하는 {keyword} 완벽 정리"],
        "궁금증형": [f"😮 설마 아직도 {keyword} 모르시나요?", f"⚠️ {keyword} 하기 전에 꼭 알아야 할 한 가지"],
        "일상형": [f"🐹 햄둥지둥 일상보고서: {keyword} 기록", f"🐾 {keyword} 찾아 삼만리! 햄둥이 탐방기"],
        "후기형": [f"💡 {keyword} 실패 없는 선택법!", f"🌟 {keyword} 내돈내산 100% 솔직 리뷰"]
    }
    return [random.choice(v) for k, v in styles.items()]

# --- 4. UI 및 햄둥이 테마 설정 ---
st.set_page_config(page_title="햄둥이 키워드 마스터", layout="wide", page_icon="🐹")
st.markdown(f"""
    <style>
    .stApp {{ background-color: #ffffff; }}
    .stButton>button {{ 
        background-color: #F4B742; color: white; border-radius: 12px; 
        font-weight: bold; width: 100%; height: 3.5em; 
    }}
    .stMetric {{ 
        background-color: #FBEECC; padding: 25px; border-radius: 15px; 
        border-left: 8px solid #F4B742; 
    }}
    .title-box {{ 
        background-color: #ffffff; padding: 15px; border-radius: 10px; 
        border: 2px dashed #F1A18E; margin-bottom: 10px; font-weight: 500;
    }}
    </style>
    """, unsafe_allow_html=True)

st.title("🐹 햄둥이의 실전 황금 키워드 분석기")
st.caption("'햄둥이의 햄둥지둥 일상보고서' 블로그 성장을 위한 전용 도구입니다. ✨")

# --- 5. 세션 상태 초기화 ---
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'target_input' not in st.session_state:
    st.session_state.target_input = ""

# --- 6. 입력 및 분석 실행 ---
input_kw = st.text_input("분석할 중심 키워드를 입력하세요", placeholder="예: 다이소 화장품")

if st.button("실시간 통합 분석 시작!"):
    if input_kw:
        results = fetch_all_keyword_data(input_kw)
        if results:
            st.session_state.analysis_results = results
            st.session_state.target_input = input_kw
            st.balloons()
            st.rerun()
    else:
        st.warning("분석할 키워드를 먼저 입력해 주세요.")

# --- 7. 결과 화면 표시 ---
if st.session_state.analysis_results:
    df_all = pd.DataFrame(st.session_state.analysis_results)
    target = st.session_state.target_input
    
    # 상단 지표
    seed_data = df_all[df_all['키워드'].str.replace(" ", "") == target.replace(" ", "")]
    if seed_data.empty: seed_data = df_all.iloc[[0]]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("월간 검색량", f"{seed_data.iloc[0]['월간 검색량']:,}회")
    col2.metric("총 문서 수", f"{seed_data.iloc[0]['총 문서 수']:,}건")
    col3.metric("경쟁 강도", f"{seed_data.iloc[0]['경쟁 강도']}")

    st.divider()

    # AI 제목 추천
    st.subheader("✍️ 햄둥이의 감성 제목 추천")
    selected_kw = st.selectbox("제목을 지을 키워드를 선택하세요", df_all['키워드'].tolist())
    
    if selected_kw:
        titles = generate_titles(selected_kw)
        for title in titles:
            st.markdown(f"<div class='title-box'>{title}</div>", unsafe_allow_html=True)
    
    st.divider()

    # 상세 리포트
    st.subheader("📊 연관 키워드 상세 분석 리포트")
    df_related = df_all[df_all['키워드'].str.replace(" ", "") != target.replace(" ", "")]
    
    if not df_related.empty:
        df_related = df_related.sort_values(by="경쟁 강도")
        st.dataframe(
            df_related.style.background_gradient(cmap='YlOrRd', subset=['경쟁 강도']),
            use_container_width=True, hide_index=True
        )
        best_rel = df_related.iloc[0]['키워드']
        st.success(f"🐹 햄둥이의 추천: **[{best_rel}]** 키워드가 현재 가장 공략하기 좋습니다!")
    else:
        st.info("💡 추가적인 연관 키워드가 발견되지 않았습니다.")