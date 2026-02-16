import os
import requests

class NaverManager:
    def __init__(self):
        self.client_id = os.environ.get("NAVER_CLIENT_ID")
        self.client_secret = os.environ.get("NAVER_CLIENT_SECRET")

    def get_image(self, keyword):
        """기사 인물/장소에 맞는 최신 이미지 URL 검색"""
        url = "https://openapi.naver.com/v1/search/image"
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        params = {"query": keyword, "display": 1, "sort": "date"}
        
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            items = res.json().get('items')
            return items[0]['link'] if items else None
        return None
