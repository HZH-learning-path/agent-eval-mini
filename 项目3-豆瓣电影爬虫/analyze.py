# -*- coding: utf-8 -*-
"""
豆瓣 TOP250 数据分析与可视化
读取 CSV 数据，生成三张图：
1. 评分分布直方图
2. 评价人数 TOP10 柱状图
3. 年份分布折线图
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

# 设置中文显示（Windows 用 SimHei，Mac 用 Arial Unicode MS）
matplotlib.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
matplotlib.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题

INPUT_FILE = "douban_top250.csv"


def main():
    # 读取 CSV
    df = pd.read_csv(INPUT_FILE)

    # 数据类型转换
    df["rating"] = df["rating"].astype(float)
    df["people_num"] = df["people_num"].astype(int)
    df["rank"] = df["rank"].astype(int)

    print("=" * 50)
    print("  豆瓣 TOP250 数据分析")
    print("=" * 50)

    # 基本统计
    print(f"\n总电影数: {len(df)}")
    print(f"平均分: {df['rating'].mean():.2f}")
    print(f"最高分: {df['rating'].max()}")
    print(f"最低分: {df['rating'].min()}")
    print(f"平均评价人数: {df['people_num'].mean():.0f}")
    print(f"最多评价人数: {df['people_num'].max()}")

    # ========== 图1：评分分布直方图 ==========
    plt.figure(figsize=(10, 6))
    plt.hist(df["rating"], bins=10, edgecolor="black", alpha=0.7, color="steelblue")
    plt.title("豆瓣 TOP250 评分分布", fontsize=14)
    plt.xlabel("评分", fontsize=12)
    plt.ylabel("电影数量", fontsize=12)
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig("rating_distribution.png", dpi=150)
    print("\n评分分布图已保存: rating_distribution.png")

    # ========== 图2：评价人数 TOP10 ==========
    top10_people = df.nlargest(10, "people_num").sort_values("people_num", ascending=True)
    plt.figure(figsize=(10, 6))
    plt.barh(top10_people["title"], top10_people["people_num"], color="coral")
    plt.title("评价人数 TOP10 电影", fontsize=14)
    plt.xlabel("评价人数", fontsize=12)
    plt.ylabel("电影名", fontsize=12)
    plt.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig("top10_people.png", dpi=150)
    print("评价人数TOP10图已保存: top10_people.png")

    # ========== 图3：年份分布 ==========
    # 提取年份（有些是"1994"这种，有些可能带其他信息，取前4位）
    df["year_clean"] = df["year"].astype(str).str[:4]
    year_counts = df["year_clean"].value_counts().sort_index()

    plt.figure(figsize=(12, 6))
    plt.plot(year_counts.index, year_counts.values, marker="o", linewidth=2, color="seagreen")
    plt.title("豆瓣 TOP250 年份分布", fontsize=14)
    plt.xlabel("年份", fontsize=12)
    plt.ylabel("电影数量", fontsize=12)
    plt.xticks(rotation=45)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("year_distribution.png", dpi=150)
    print("年份分布图已保存: year_distribution.png")

    # ========== 额外：类型统计 ==========
    print("\n类型统计（前10）:")
    all_genres = []
    for g in df["genre"].dropna():
        all_genres.extend([x.strip() for x in g.split()])
    from collections import Counter
    genre_counts = Counter(all_genres).most_common(10)
    for genre, count in genre_counts:
        print(f"  {genre}: {count} 部")

    print("\n分析完成！")


if __name__ == "__main__":
    main()
