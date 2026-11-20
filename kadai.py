import sqlite3
import time
from bs4 import BeautifulSoup
import requests

DB_NAME = "google_repos.db"
BASE_URL = "https://github.com/orgs/google/repositories"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Applewebkit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def init_db(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute