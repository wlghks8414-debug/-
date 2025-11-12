# 1. 라이브러리 임포트
import streamlit as st
import requests
import pandas as pd
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import time

# --- (★ 1. 여기에 1단계에서 발급받은 v4 토큰을 붙여넣으세요! ★) ---
TMDB_API_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIxNTliMjYwNjM1Zjk5OTE4NDA1YWM3MzY2ZWNhNDA0YyIsIm5iZiI6MTc2Mjk1NzcwOS44LCJzdWIiOiI2OTE0OTk4ZDkxYTM4MTRjZWJkZDJkNzciLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.RpvGVLDillV1uE3HAJICAYxfXv14Ynx1beC3iiBiJr4"
# -----------------------------------------------------------------


# --- 2. "한글 -> 영어" 검색 함수 ---
@st.cache_data(show_spinner=False) # API 검색 결과를 잠시 캐싱(저장)
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
            return movie['original_title'], movie['title'] # 영어 원제, 한글 제목
        else:
            return None, None
    except Exception as e:
        st.error(f"TMDB API 검색 오류: {e}")
        return None, None

# --- 3. "영어 -> 한글" 번역 함수 ---
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
                if movie['original_title'].lower() == english_title.lower():
                    return movie['title'] # 정확히 일치하는 한글 제목
            return data['results'][0]['title'] # 없으면 첫 번째 결과
        else:
            return english_title
    except Exception:
        return english_title # 오류 시 영어 원제 반환

# --- 4. "추천 엔진" 준비 함수 (★경로 수정됨★) ---
@st.cache_data(show_spinner="추천 엔진을 준비하는 중입니다... (최초 1회 20초 소요)")
def setup_recommendation_engine():
    # 이 코드가 GitHub/Streamlit 서버에서 실행될 때는
    # .py 파일과 .csv 파일이 같은 폴더에 있게 됩니다.
    file_path = "tmdb_5000_movies.csv" 

    try:
        movies_df = pd.read_csv(file_path) 
    except FileNotFoundError:
        st.error(f"데이터 파일('tmdb_5000_movies.csv')을 찾을 수 없습니다. GitHub에 파일이 업로드되었는지 확인하세요.")
        return None, None, None
    except Exception as e:
        st.error(f"데이터 파일 로딩 중 오류: {e}")
        return None, None, None

    movies_df['overview'] = movies_df['overview'].fillna('')
    tfidf_vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf_vectorizer.fit_transform(movies_df['overview'])
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
    indices = pd.Series(movies_df.index, index=movies_df['title']).drop_duplicates()
    return movies_df, cosine_sim, indices

# --- 5. 추천 실행 함수 ---
def get_recommendations(original_title, df, cosine_sim_matrix, indices_map):
    try:
        idx = indices_map[original_title]
    except KeyError:
        try:
            if ', The' in original_title:
                 title_fixed = 'The ' + original_title.replace(', The', '')
                 idx = indices_map[title_fixed]
            else: raise KeyError 
        except KeyError:
             return pd.Series(dtype='object')
    
    sim_scores = list(enumerate(cosine_sim_matrix[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    top_n_indices = [i[0] for i in sim_scores[1:11]]
    return df['title'].iloc[top_n_indices] # 영어 원제 10개 리스트 반환


# --- 6. Streamlit 웹페이지 구성 (메인 코드) ---
st.set_page_config(page_title="영화 추천기", layout="centered")
st.title("🍿 줄거리 기반 영화 추천기")
st.markdown("좋아하는 영화의 한글 제목을 입력하면, 줄거리가 비슷한 영화 10편을 추천해 드립니다.")

# (1) 추천 엔진 로드 (최초 1회 실행)
df, sim_matrix, idx_map = setup_recommendation_engine()

if df is not None:
    # (2) 사용자에게 웹페이지 입력창 제공
    korean_title_input = st.text_input("영화 제목을 한글로 입력하세요 (예: 인셉션, 헤어질 결심)")

    # (3) '추천 받기' 버튼
    if st.button("추천 받기 🎬"):
        if korean_title_input:
            with st.spinner(f"'{korean_title_input}'와(과) 비슷한 영화를 찾는 중..."):
                # (4) 한글 -> 영어 원제
                original_title, display_title = get_original_title_from_tmdb(korean_title_input, TMDB_API_TOKEN)

                if original_title:
                    # (5) 영어 원제 -> 추천 목록(영어 원제 10개)
                    recommendations_eng = get_recommendations(original_title, df, sim_matrix, idx_map)
                    
                    if not recommendations_eng.empty:
                        st.subheader(f"✅ '{display_title}'와(과) 비슷한 영화 TOP 10")
                        
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
            st.warning("영화 제목을 입력해주세요!")