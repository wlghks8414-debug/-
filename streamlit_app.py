# 1. 라이브러리 임포트 (Pandas, Sklearn 모두 삭제됨)
import streamlit as st
import requests
import time

# --- (★ 1. 여기에 1단계에서 발급받은 v4 토큰을 붙여넣으세요!) ---
TMDB_API_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIxNTliMjYwNjM1Zjk5OTE4NDA1YWM3MzY2ZWNhNDA0YyIsIm5iZiI6MTc2Mjk1NzcwOS44LCJzdWIiOiI2OTE0OTk4ZDkxYTM4MTRjZWJkZDJkNzciLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.RpvGVLDillV1uE3HAJICAYxfXv14Ynx1beC3iiBiJr4"
# -----------------------------------------------------------------

HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {TMDB_API_TOKEN}"
}

# --- 2. "한글 -> 영화 ID" 검색 함수 (수정됨) ---
@st.cache_data(show_spinner=False)
def search_movie(korean_title):
    """
    TMDB API를 사용해 한글 제목으로 영화를 검색하고,
    영화의 고유 ID와 한글 제목을 반환합니다.
    """
    print(f"\n'{korean_title}'의 영화 정보를 TMDB에서 검색합니다...")
    search_url = "https://api.themoviedb.org/3/search/movie"
    params = {'query': korean_title, 'language': 'ko-KR'}

    try:
        response = requests.get(search_url, headers=HEADERS, params=params)
        response.raise_for_status() 
        data = response.json() 
        
        if data['results']:
            movie = data['results'][0]
            # (예: 838209, "파묘") 반환
            return movie['id'], movie['title']
        else:
            return None, None # 검색 결과 없음
    except Exception as e:
        st.error(f"TMDB API (영화 검색) 오류: {e}")
        return None, None

# --- 3. (★새로운 핵심★) "ID -> 추천 목록" 함수 ---
@st.cache_data(show_spinner=False)
def get_recommendations(movie_id):
    """
    영화 ID를 기준으로, TMDB의 자체 추천 목록을 한글로 받아옵니다.
    """
    print(f"\nID '{movie_id}'의 추천 목록을 TMDB에서 검색합니다...")
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/recommendations"
    params = {'language': 'ko-KR'} # 추천 결과를 한글로 받음

    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['results']:
            # 추천 영화 목록 (딕셔너리 리스트)을 반환
            return data['results']
        else:
            return [] # 추천 결과가 없는 경우
            
    except Exception as e:
        st.error(f"TMDB API (추천 검색) 오류: {e}")
        return []

# --- 4. Streamlit 웹페이지 구성 (메인 코드) ---
st.set_page_config(page_title="영화 추천기", layout="centered")
st.title("영화 추천")
st.markdown("좋아하는 영화의 한글 제목을 입력하면, 비슷한 영화 10편을 추천해 드립니다.")

# (1) 사용자에게 웹페이지 입력창 제공
korean_title_input = st.text_input("영화 제목을 한글로 입력하세요")

# (2) '추천 받기' 버튼
if st.button("추천 받기"):
    if korean_title_input:
        with st.spinner(f"'{korean_title_input}'와(과) 비슷한 영화를 찾는 중..."):
            
            # (3) 한글 제목으로 영화 ID와 정확한 한글 제목 검색
            movie_id, display_title = search_movie(korean_title_input)

            if movie_id:
                # (4) 찾은 영화 ID로 추천 목록 요청
                recommendations = get_recommendations(movie_id)
                
                if recommendations:
                    st.subheader(f"'{display_title}'와(과) 비슷한 영화 TOP 10")
                    
                    # (5) 결과(딕셔너리 리스트)를 순서대로 출력
                    for i, movie in enumerate(recommendations[:10]): # 최대 10개
                        st.write(f"{i+1}. {movie['title']} (원제: {movie['original_title']})")
                    st.markdown("---")
                else:
                    st.error(f"'{display_title}'에 대한 추천 목록을 찾지 못했습니다. (TMDB에 데이터 부족)")
            else:
                st.error(f"TMDB에서 '{korean_title_input}'의 영화 정보를 찾지 못했습니다.")
    else:
        st.warning("영화 제목을 입력해주세요!")