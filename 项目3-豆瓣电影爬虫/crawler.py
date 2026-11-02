# -*- coding: utf-8 -*-
"""
豆瓣电影 TOP250 爬虫
爬取：排名、电影名、评分、评价人数、年份、国家、类型
保存为 CSV 文件
"""
import requests
from bs4 import BeautifulSoup
import csv
import time
import random

BASE_URL = "https://movie.douban.com/top250"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
OUTPUT_FILE = "douban_top250.csv"
TOTAL_PAGES = 10


def parse_page(html):
    soup = BeautifulSoup(html, "html.parser")
    movies = []
    items = soup.find_all("div", class_="item")

    for item in items:
        try:
            rank = item.find("em").get_text()
            title = item.find("span", class_="title").get_text()
            rating = item.find("span", class_="rating_num").get_text()
            people_num = item.find("div", class_="star").find_all("span")[-1].get_text()
            people_num = people_num.replace("人评价", "").strip()

            info = item.find("div", class_="bd").find("p").get_text().strip()
            lines = info.split("\n")
            if len(lines) >= 2:
                second_line = lines[1].strip()
                parts = second_line.split("/")
                year = parts[0].strip() if len(parts) > 0 else ""
                country = parts[1].strip() if len(parts) > 1 else ""
                genre = parts[2].strip() if len(parts) > 2 else ""
            else:
                year = country = genre = ""

            movies.append({
                "rank": rank, "title": title, "rating": rating,
                "people_num": people_num, "year": year,
                "country": country, "genre": genre
            })
        except Exception as e:
            print(f"  解析失败: {e}")
            continue

    return movies


def main():
    print("=" * 50)
    print("  豆瓣电影 TOP250 爬虫")
    print("=" * 50)

    all_movies = []

    for page in range(TOTAL_PAGES):
        start = page * 25
        url = f"{BASE_URL}?start={start}"
        print(f"\n[第{page+1}/{TOTAL_PAGES}页] {url}")

        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()

            movies = parse_page(response.text)
            all_movies.extend(movies)
            print(f"  获取 {len(movies)} 部")

            wait_time = random.uniform(1, 3)
            time.sleep(wait_time)
        except Exception as e:
            print(f"  请求失败: {e}")
            break

    if all_movies:
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "rank", "title", "rating", "people_num", "year", "country", "genre"
            ])
            writer.writeheader()
            writer.writerows(all_movies)
        print(f"\n完成！共 {len(all_movies)} 部，已保存到 {OUTPUT_FILE}")
    else:
        print("\n没有获取到数据")


if __name__ == "__main__":
    main()
