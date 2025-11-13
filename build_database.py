
import requests
import pandas as pd
import time
import os

# --- (★ 1. 여기에 1단계에서 발급받은 v4 토큰을 붙여넣으세요!) ---
TMDB_API_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIxNTliMjYwNjM1Zjk5OTE4NDA1YWM3MzY2ZWNhNDA0YyIsIm5iZiI6MTc2Mjk1NzcwOS44LCJzdWIiOiI2OTE0OTk4ZDkxYTM4MTRjZWJkZDJkNzciLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.RpvGVLDillV1uE3HAJICAYxfXv14Ynx1beC3iiBiJr4"
# -----------------------------------------------------------------

HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {TMDB_API_TOKEN}"
}

def fetch_movies_by_year(year):
    """
    특정 연도의 인기 영화 100편(5페이지) 정보를 가져옵니다.
    (줄거리, 제목 모두 '영어'로 가져와서 Kaggle 데이터와 형식을 맞춥니다.)
    """
    print(f"{year}년도 영화 데이터 수집 중...")
    movies_of_year = []
    
    for page in range(1, 6): # 1페이지당 20개 * 5페이지 = 100편
        url = "https://api.themoviedb.org/3/discover/movie"
        params = {
            'language': 'en-US', # (중요!) 추천 엔진의 일관성을 위해 영어로 수집
            'primary_release_year': year,
            'sort_by': 'popularity.desc', # 인기순 정렬
            'page': page
        }
        
        try:
            response = requests.get(url, headers=HEADERS, params=params)
            response.raise_for_status()
            data = response.json()
            
            for movie in data['results']:
                # 줄거리가 없는 영화는 제외
                if movie.get('overview'):
                    movies_of_year.append({
                        'title': movie['title'], # 영어 제목
                        'original_title': movie['original_title'], # 영어 원제
                        'overview': movie['overview'], # 영어 줄거리
                        'release_date': movie.get('release_date')
                    })
            
            time.sleep(0.3) # (매우 중요!) API 차단을 피하기 위해 0.3초 대기
            
        except Exception as e:
            print(f"{year}년 {page}페이지 수집 오류: {e}")
            
    return movies_of_year

# --- 메인 실행 ---
if __name__ == "__main__":
    all_movies_list = []
    
    # 2010년부터 2025년까지 반복 (필요하면 2000년 등으로 수정 가능)
    for year_to_fetch in range(2010, 2026):
        all_movies_list.extend(fetch_movies_by_year(year_to_fetch))
        
    print(f"\n총 {len(all_movies_list)}편의 영화 데이터를 수집했습니다.")
    
    df = pd.DataFrame(all_movies_list)
    
    # (중요!) 저장할 파일 이름
    new_filename = "my_new_database.csv"
    
    # 현재 스크립트가 있는 폴더에 저장
    df.to_csv(new_filename, index=False, encoding='utf-8-sig')
    
    print(f"'{new_filename}' 파일로 성공적으로 저장했습니다!")
    print(f"저장 위치: {os.path.abspath(new_filename)}")
