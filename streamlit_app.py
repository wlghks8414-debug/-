# 1. 라이브러리 임포트
import streamlit as st
import requests
import pandas as pd
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import time

# --- (★ 1. 여기에 1단계에서 발급받은 v4 토큰을 붙여넣으세요!) ---
TMDB_API_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIxNTliMjYwNjM1Zjk5OTE4NDA1YWM3MzY2ZWNhNDA0YyIsIm5iZiI6MTc2Mjk1NzcwOS44LCJzdWIiOiI2OTE0OTk4ZDkxYTM4MTRjZWJkZDJkNzciLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.RpvGVLDillV1uE3HAJICAYxfXv14Ynx1beC3iiBiJr4"
# -----------------------------------------------------------------

# --- 2. "한글 -> 영어" 검색 함수 (TMDB API) ---
@st.cache_data(show_spinner=False)
def get_original_title_from_tmdb(korean_title, api_token):
    search_url = "https://api.themoviedb.org/3/search/movie"
    params = {'query': korean_title, 'language': 'ko-KR'}
    headers = {"accept": "application/json", "Authorization": f"Bearer {api_token}"}
    try:
        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if data['results']:
            movie = data['results'][0]
            # (중요!) 이제 'title'과 'original_title'이 모두 있는 새 DB를 사용하므로,
            # 'original_title' (영어 원제)을 반환합니다.
            return movie['original_title'], movie['title']
        else:
            return None, None
    except Exception as e:
        st.error(f"TMDB API 검색 오류: {e}")
        return None, None

# --- 3. "영어 -> 한글" 번역 함수 (TMDB API) ---
@st.cache_data(show_spinner=False)
def get_korean_title_from_tmdb(english_title, api_token):
    search_url = "https://api.themoviedb.org/3/search/movie"
    params = {'query': english_title, 'language': 'ko-KR'} 
    headers = {"accept": "application/json", "Authorization": f"Bearer {api_token}"}
    try:
        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if data['results']:
            for movie in data['results']:
                # 'original_title'이 정확히 일치하는 것을 우선 찾음
                if movie['original_title'].lower() == english_title.lower():
                    return movie['title']
            return data['results'][0]['title'] # 없으면 첫 번째 결과
        else:
            return english_title
    except Exception:
        return english_title

# --- 4. "추천 엔진" 준비 함수 (★새 DB 파일 사용★) ---
@st.cache_data(show_spinner="최신 추천 엔진을 준비합니다... (최초 1회 10초 소요)")
def setup_recommendation_engine():
    
    # (★ 핵심 수정!) 낡은 Kaggle 파일 대신, 우리가 만든 새 DB 파일을 읽습니다.
    file_path = "my_new_database.csv" 

    try:
        movies_df = pd.read_csv(file_path) 
    except FileNotFoundError:
        st.error(f"데이터 파일('my_new_database.csv')을 찾을 수 없습니다. GitHub에 파일이 업로드되었는지 확인하세요.")
        return None, None, None, None # 4개 반환
    except Exception as e:
        st.error(f"데이터 파일 로딩 중 오류: {e}")
        return None, None, None, None # 4개 반환

    movies_df['overview'] = movies_df['overview'].fillna('')
    
    tfidf_vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf_vectorizer.fit_transform(movies_df['overview'])
    
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
    
    # (★ 핵심 수정!) 
    # 새 DB에는 'title'(영어)과 'original_title'(영어)이 모두 있으므로
    # 두 가지 경우의 수에 대비해 인덱스 맵을 2개 만듭니다.
    indices_title = pd.Series(movies_df.index, index=movies_df['title']).drop_duplicates()
    indices_original = pd.Series(movies_df.index, index=movies_df['original_title']).drop_duplicates()
    
    print("\n--- 3. 최신 추천 엔진 준비 완료! ---")
    # (★ 핵심 수정!) 4개의 값을 반환합니다.
    return movies_df, cosine_sim, indices_title, indices_original


# --- 5. 추천 실행 함수 (★수정됨★) ---
def get_recommendations(original_title, df, cosine_sim_matrix, indices_title, indices_original):
    """
    '영어 원제'를 기준으로, 유사도가 높은 상위 10개 영화의 '영어 원제'를 반환합니다.
    """
    idx = None
    try:
        # 1. 'original_title' 컬럼에서 먼저 검색
        idx = indices_original[original_title]
    except KeyError:
        # 2. 'original_title'에 없으면, 'title' 컬럼에서도 검색
        try:
            idx = indices_title[original_title]
        except KeyError:
            # 3. 'The'가 붙는 영화 처리 (예: 'Dark Knight, The' -> 'The Dark Knight')
            try:
                if ', The' in original_title:
                     title_fixed = 'The ' + original_title.replace(', The', '')
                     idx = indices_original[title_fixed]
                else: raise KeyError
            except KeyError:
                 print(f"'{original_title}'이(가) 로컬 DB(CSV)에 없습니다.")
                 return pd.Series(dtype='object') # 빈 Series 반환

    sim_scores = list(enumerate(cosine_sim_matrix[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    top_n_indices = [i[0] for i in sim_scores[1:11]]
    
    # (★ 핵심 수정!) Kaggle의 'title' 대신 'original_title'을 반환해야 
    # '헤어질 결심' 같은 영화가 다음 단계 번역에서 꼬이지 않습니다.
    return df['original_title'].iloc[top_n_indices]


# --- 6. Streamlit 웹페이지 구성 (메인 코드) ---
st.set_page_config(page_title="영화 추천기", layout="centered")
st.title("영화 추천기")
st.markdown("좋아하는 영화의 한글 제목을 입력하면, 줄거리가 비슷한 영화 10편을 추천해 드립니다.")

# (1) 추천 엔진 로드 (4개 값 반환)
df, sim_matrix, idx_map, idx_map_orig = setup_recommendation_engine()

if df is not None:
    # (2) 사용자 입력창
    korean_title_input = st.text_input("영화 제목을 한글로 입력하세요")

    # (3) '추천 받기' 버튼
    if st.button("추천 받기"):
        if korean_title_input:
            with st.spinner(f"'{korean_title_input}'와(과) 비슷한 영화를 찾는 중..."):
                
                # (4) 한글 -> 영어 원제
                original_title, display_title = get_original_title_from_tmdb(korean_title_input, TMDB_API_TOKEN)

                if original_title:
                    # (5) 영어 원제 -> 추천 목록(영어 원제 10개)
                    recommendations_eng = get_recommendations(original_title, df, sim_matrix, idx_map, idx_map_orig)
                    
                    if not recommendations_eng.empty:
                        st.subheader(f"'{display_title}'와(과) 비슷한 영화 TOP 10")
                        
                        # (6) 추천 목록(영어 10개) -> 한글 제목으로 번역
                        for i, eng_title in enumerate(recommendations_eng):
                            kor_title = get_korean_title_from_tmdb(eng_title, TMDB_API_TOKEN)
                            if kor_title and kor_title != eng_title:
                                st.write(f"{i+1}. {kor_title} (원제: {eng_title})")
                            else:
                                st.write(f"{i+1}. {eng_title}")
                            time.sleep(0.05) # API 과호출 방지
                    else:
                        st.error(f"Kaggle CSV 데이터셋에서 '{original_title}'의 추천 목록을 찾지 못했습니다.")
                else:
                    st.error(f"TMDB에서 '{korean_title_input}'의 영화 정보를 찾지 못했습니다.")
        else:
            st.warning("영화 제목을 입력해주세요")