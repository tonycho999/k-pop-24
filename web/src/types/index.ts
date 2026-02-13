// src/types/index.ts

export interface LiveNewsItem {
  id: string;
  created_at: string;
  category: string;
  rank: number;       // 1 ~ 30
  keyword: string;    // 예: "뉴진스"
  title: string;
  summary: string;
  link: string;
  image_url: string | null;
  score: number;
  likes: number;
  dislikes: number;
}

export interface RankingItemData {
  id: string;
  category: string;
  rank: number;
  keyword: string;
  delta: string;      // "NEW", "-", "▲1" 등
  image_url: string | null;
}
