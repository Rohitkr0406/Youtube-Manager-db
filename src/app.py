import sqlite3
import webbrowser
import requests
import os
from contextlib import contextmanager
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

DB_NAME = "videos.db"
APIFY_TOKEN = os.getenv("APIFY_TOKEN") or os.getenv("APIFY_API_TOKEN")

# =====================================================================
# DATABASE OPERATIONS
# =====================================================================


@contextmanager
def get_db_connection():
    """Centralized DB connection — single place to manage connection lifecycle."""
    conn = sqlite3.connect(DB_NAME)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url   TEXT NOT NULL UNIQUE
            )
        ''')


def fetch_all_videos():
    with get_db_connection() as conn:
        return conn.execute('SELECT id, title, url FROM videos').fetchall()


def add_video_to_db(title, url):
    try:
        with get_db_connection() as conn:
            conn.execute(
                'INSERT INTO videos (title, url) VALUES (?, ?)', (title, url))
        return True
    except sqlite3.IntegrityError:
        print("⚠️  This URL already exists in your manager.")
        return False


def update_video_in_db(video_id, field, new_value):
    # Whitelist the field — never interpolate column names from user input
    allowed_fields = {"title", "url"}
    if field not in allowed_fields:
        raise ValueError(f"Invalid field: {field}")
    with get_db_connection() as conn:
        conn.execute(
            f'UPDATE videos SET {field} = ? WHERE id = ?',
            (new_value,
             video_id))


def delete_video_from_db(video_id):
    with get_db_connection() as conn:
        conn.execute('DELETE FROM videos WHERE id = ?', (video_id,))


# =====================================================================
# UTILITY HELPER FUNCTIONS
# =====================================================================

def normalize_url(url: str) -> str:
    """Ensure URL has a proper scheme."""
    url = url.strip()
    if url and not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


def get_youtube_title(url: str) -> str | None:
    url = normalize_url(url)
    try:
        oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
        response = requests.get(oembed_url, timeout=10)
        if response.status_code == 200:
            return response.json().get('title')
    except requests.exceptions.RequestException:
        pass
    return None


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def download_video_apify(url: str):
    if not APIFY_TOKEN:
        print("⚠️  Apify API token not found. Set APIFY_TOKEN in your .env file.")
        return

    print("Connecting to Apify Cloud Platform...")
    client = ApifyClient(APIFY_TOKEN)

    try:
        print("Running the downloader actor...")
        run = client.actor("streamers/youtube-video-downloader").call(
            run_input={"videos": [{"url": url}]},
            memory_mbytes=1024
        )

        # Support both dict (modern SDK) and object (older SDK) responses
        dataset_id = (
            run.get("defaultDatasetId") if isinstance(
                run, dict) else getattr(
                run, "default_dataset_id", getattr(
                    run, "defaultDatasetId", None)))

        print("Fetching download data from the dataset...")
        dataset_items = list(client.dataset(str(dataset_id)).iterate_items())

        download_url = _extract_download_url(dataset_items, url)

        if download_url:
            print("\n🎉 Download link generated!")
            print(f"🔗 Link: {download_url}")
            print("🍿 Launching browser...")
            webbrowser.open(download_url)
        else:
            print("\n❌ Could not extract a download URL from the response.")
            if not dataset_items:
                print("⚠️  Result dataset is empty — the actor may have failed.")
            else:
                print(
                    f"   Found {
                        len(dataset_items)} item(s), none had a valid link.")
                print(
                    f"   Keys in first result: {
                        list(
                            dataset_items[0].keys())}")
            print(
                f"💾 Check the run console: https://console.apify.com/storage/datasets/{dataset_id}")

    except Exception as e:
        print(f"\n⚠️  Apify API error: {e}")


def _extract_download_url(items: list, original_url: str) -> str | None:
    """Try known field names, then fall back to any non-YouTube URL."""
    KNOWN_FIELDS = (
        "downloadUrl",
        "downloadedFileUrl",
        "videoUrl",
        "videoOnlyUrl",
        "fileUrl")
    for item in items:
        for field in KNOWN_FIELDS:
            if item.get(field):
                return item[field]
        # Fallback: any 'url' that isn't the original YouTube link
        candidate = item.get("url", "")
        if candidate and "youtube.com" not in candidate and "youtu.be" not in candidate:
            return candidate
    return None


def display_video_list(videos: list) -> bool:
    """Print video list. Returns False (and prints a hint) when list is empty."""
    if not videos:
        print("📭 No videos found. Add some videos first!")
        return False
    print("\n" + "=" * 90)
    print(f"{'#':<6} | {'Title':<50} | URL")
    print("-" * 90)
    for i, (_db_id, title, url) in enumerate(videos, start=1):
        short_title = title[:47] + '...' if len(title) > 50 else title
        print(f"{i:<6} | {short_title:<50} | {url}")
    print("=" * 90 + "\n")
    return True


def get_valid_index(videos: list, prompt: str) -> int | str:
    """Prompt user for a 1-based list index. Returns int index or 'back'."""
    while True:
        raw = input(prompt).strip()
        if raw.lower() == 'n':
            return 'back'
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(videos):
                return idx
        print(
            f"  Please enter a number between 1 and {
                len(videos)}, or 'n' to go back.")


# =====================================================================
# CORE FEATURES
# =====================================================================

def watch_video():
    clear_screen()
    print("--- 👀 Watch Video ---")
    videos = fetch_all_videos()
    if not display_video_list(videos):
        return

    choice = get_valid_index(
        videos, "Enter index to watch (or n to go back): ")
    if choice == 'back':
        return
    _, title, url = videos[choice]
    webbrowser.open(url)
    print(f"Opening: {title}...")


def add_video():
    clear_screen()
    print("--- ➕ Add New Video ---")
    url = normalize_url(input("Enter the YouTube video URL: "))
    if not url:
        print("URL cannot be empty.")
        return

    print("Fetching video details...")
    title = get_youtube_title(url)

    if title:
        print(f"Found: {title}")
        if input("Keep this title? (y/n): ").strip().lower() != 'y':
            title = input("Enter custom title: ").strip()
    else:
        print("Could not fetch title automatically.")
        title = input("Enter the video title manually: ").strip()

    if not title:
        print("Title cannot be empty. Video not added.")
        return

    if add_video_to_db(title, url):
        print("✅ Video added successfully!")


def update_video():
    clear_screen()
    print("--- ✏️ Update Video Details ---")
    videos = fetch_all_videos()
    if not display_video_list(videos):
        return

    choice = get_valid_index(
        videos, "Enter index to update (or n to go back): ")
    if choice == 'back':
        return

    video_id, current_title, _ = videos[choice]
    print(f"Selected: {current_title}")
    print("1. Update Title\n2. Update URL")

    field_map = {"1": "title", "2": "url"}
    field = field_map.get(input("Choice (1-2): ").strip())
    if not field:
        print("Invalid choice.")
        return

    new_value = input(f"Enter new {field}: ").strip()
    if not new_value:
        print(f"{field.capitalize()} cannot be empty.")
        return

    update_video_in_db(video_id, field, new_value)
    print(f"✅ {field.capitalize()} updated successfully!")


def delete_video():
    clear_screen()
    print("--- 🗑️ Delete Video ---")
    videos = fetch_all_videos()
    if not display_video_list(videos):
        return

    choice = get_valid_index(
        videos, "Enter index to delete (or n to go back): ")
    if choice == 'back':
        return

    video_id, title, _ = videos[choice]
    print(f"Selected: {title}")
    if input("Are you sure? (y/n): ").strip().lower() == 'y':
        delete_video_from_db(video_id)
        print("✅ Video deleted.")
    else:
        print("Deletion cancelled.")


def download_video():
    clear_screen()
    print("--- 📥 Download Video ---")
    videos = fetch_all_videos()

    print("1. Download from saved list\n2. Enter custom URL\n3. Go back")
    choice = input("Choice (1-3): ").strip()

    if choice == '1':
        if not display_video_list(videos):
            return
        idx = get_valid_index(
            videos, "Enter index to download (or n to go back): ")
        if idx != 'back':
            download_video_apify(videos[idx][2])

    elif choice == '2':
        url = normalize_url(input("Enter YouTube URL: "))
        if url:
            download_video_apify(url)
        else:
            print("Invalid URL.")

    elif choice == '3':
        return

    else:
        print("Invalid choice.")


# =====================================================================
# MAIN
# =====================================================================

MENU = """
📺 === YOUTUBE VIDEO MANAGER ===
  1. Watch / Open Video
  2. Add New Video
  3. Update Video Details
  4. Download Video
  5. Delete Video
  6. Exit
"""

ACTIONS = {
    "1": watch_video,
    "2": add_video,
    "3": update_video,
    "4": download_video,
    "5": delete_video,
}


def main():
    init_db()
    while True:
        print(MENU)
        choice = input("Enter choice (1-6): ").strip()
        if choice == '6':
            clear_screen()
            print("Thanks for using YouTube Video Manager. Bye!")
            break
        action = ACTIONS.get(choice)
        if action:
            action()
        else:
            print("Invalid choice. Please try again.")
        input("\nPress Enter to return to the main menu...")
        clear_screen()


if __name__ == "__main__":
    main()
