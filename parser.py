import httpx
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta


def parse_views(views_text: str) -> int:
    """Преобразует '12.3K' -> 12300"""
    if not views_text:
        return 0
    views_text = views_text.strip().upper().replace(" ", "")
    try:
        if "K" in views_text:
            return int(float(views_text.replace("K", "")) * 1000)
        elif "M" in views_text:
            return int(float(views_text.replace("M", "")) * 1_000_000)
        else:
            return int(re.sub(r"[^\d]", "", views_text))
    except:
        return 0


def fetch_channel(channel: str, hours: int = 24) -> list:
    """Парсит публичный канал через t.me/s/"""
    channel = channel.lstrip("@").strip()
    url = f"https://t.me/s/{channel}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        r.raise_for_status()
    except Exception as e:
        print(f"Ошибка загрузки {channel}: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")

    # Название канала
    title_el = soup.find("div", class_="tgme_channel_info_header_title")
    channel_title = title_el.get_text(strip=True) if title_el else f"@{channel}"

    posts = soup.find_all("div", class_="tgme_widget_message_wrap")
    results = []
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    for post in posts:
        # Текст поста
        text_el = post.find("div", class_="tgme_widget_message_text")
        if not text_el:
            continue
        text = text_el.get_text(separator="\n").strip()
        if not text:
            continue

        # Просмотры
        views_el = post.find("span", class_="tgme_widget_message_views")
        views = parse_views(views_el.get_text() if views_el else "0")

        # Дата
        date_el = post.find("time")
        post_date = None
        if date_el and date_el.get("datetime"):
            try:
                post_date = datetime.fromisoformat(
                    date_el["datetime"].replace("Z", "+00:00")
                ).replace(tzinfo=None)
            except:
                pass

        if post_date and post_date < cutoff:
            continue

        # Ссылка на пост
        link_el = post.find("a", class_="tgme_widget_message_date")
        post_url = link_el["href"] if link_el else f"https://t.me/{channel}"

        results.append({
            "channel": f"@{channel}",
            "channel_title": channel_title,
            "text": text,
            "views": views,
            "url": post_url,
            "date": post_date,
        })

    return results


def get_top_posts(channels: list, hours: int = 24, top_n: int = 5) -> list:
    """Собирает и ранжирует посты из всех каналов"""
    all_posts = []

    for channel in channels:
        posts = fetch_channel(channel, hours)
        all_posts.extend(posts)
        print(f"  {channel}: найдено {len(posts)} постов")

    # Сортировка по просмотрам
    all_posts.sort(key=lambda x: x["views"], reverse=True)
    return all_posts[:top_n]
