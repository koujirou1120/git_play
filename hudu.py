import sqlite3
import time
from bs4 import BeautifulSoup
import requests

DB_NAME = "google_repos.db"
BASE_URL = "https://github.com/orgs/google/repositories"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def init_db(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                language TEXT,
                stars INTEGER NOT NULL DEFAULT 0
            )
            """
        )


def parse_stars(text: str) -> int:
    cleaned = text.strip().lower().replace(",", "")
    if not cleaned:
        return 0
    if cleaned.endswith("k"):
        return int(float(cleaned[:-1]) * 1000)
    return int(cleaned) if cleaned.isdigit() else 0


def scrape_google_repos(max_pages: int = 3) -> list[tuple[str, str, int]]:
    results: list[tuple[str, str, int]] = []

    for page in range(1, max_pages + 1):
        url = BASE_URL if page == 1 else f"{BASE_URL}?page={page}"
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()

        soup = BeautifulSoup(res.text, "html.parser")

        # リポジトリごとの要素を抽出（GitHubのHTML構造変化に備えて複数パターン対応）
        repo_links = soup.select('a[itemprop="name codeRepository"]')
        if not repo_links:
            repo_links = soup.select('a[href^="/google/"]')

        page_count = 0
        seen_names: set[str] = set()

        for link in repo_links:
            href = link.get("href", "").strip("/")
            parts = href.split("/")
            # /google/<repo_name> の形式のみ対象（issues, pulls, tree などを除外）
            if len(parts) != 2 or parts[0].lower() != "google":
                continue

            repo_name = parts[1]
            if not repo_name or repo_name in seen_names:
                continue
            seen_names.add(repo_name)

            # 親コンテナから言語とスター数を探す
            container = link.find_parent("li") or link.find_parent("div")
            language = "Unknown"
            stars = 0

            if container:
                lang_el = container.select_one('[itemprop="programmingLanguage"]')
                if lang_el and lang_el.get_text(strip=True):
                    language = lang_el.get_text(strip=True)

                else:
                    known_langs = {
                        "Python", "Java", "C++", "Go", "JavaScript", "TypeScript",
                        "C", "Rust", "Kotlin", "Dart", "HTML", "CSS", "Shell",
                        "C#", "Ruby", "PHP", "Swift", "Scala", "Jupyter Notebook"
                    }
                    for sp in container.find_all("span"):
                        txt = sp.get_text(strip=True)
                        if txt in known_langs:
                            language = txt
                            break

                # スター数リンク（例: /google/repo/stargazers）を探す
                star_el = container.select_one('a[href$="/stargazers"]')
                if star_el:
                    stars = parse_stars(star_el.get_text(" ", strip=True))

            results.append((repo_name, language, stars))
            page_count += 1

        print(f"Page {page}: {page_count} 件取得")

        # 課題要件：必ず time.sleep(1) を入れる
        time.sleep(1)

        if page_count == 0:
            break

    return results


def save_and_display(rows: list[tuple[str, str, int]]) -> None:
    conn = sqlite3.connect(DB_NAME)
    try:
        init_db(conn)
        with conn:
            conn.executemany(
                """
                INSERT INTO repositories (name, language, stars)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    language = excluded.language,
                    stars = excluded.stars
                """,
                rows,
            )

        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, language, stars FROM repositories ORDER BY stars DESC, name ASC"
        )
        records = cursor.fetchall()

        print("\n--- 保存されたデータ（SELECT結果）---")
        for name, language, stars in records:
            print(f"リポジトリ名: {name} | 主要な言語: {language} | スター数: {stars}")
        print(f"\n合計件数: {len(records)} 件")
    finally:
        conn.close()


if __name__ == "__main__":
    scraped_data = scrape_google_repos(max_pages=3)
    save_and_display(scraped_data)