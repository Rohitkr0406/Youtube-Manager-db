import sqlite3
import webbrowser
import requests
import os
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

DB_NAME = "videos.db"
APIFY_TOKEN = os.getenv("APIFY_TOKEN", os.getenv("APIFY_API_TOKEN", "APIFY_API_TOKEN"))

# =====================================================================
# DATABASE OPERATIONS
# =====================================================================

def init_db():
	with sqlite3.connect(DB_NAME) as conn:
		cursor = conn.cursor()
		cursor.execute('''
			CREATE TABLE IF NOT EXISTS videos (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				title TEXT NOT NULL,
				url TEXT NOT NULL
			)
		''')
		conn.commit()

def fetch_all_videos():
	with sqlite3.connect(DB_NAME) as conn:
		cursor = conn.cursor()
		cursor.execute('SELECT * FROM videos')
		return cursor.fetchall()

def add_video_to_db(title,url):
	with sqlite3.connect(DB_NAME) as conn:
		cursor = conn.cursor()
		cursor.execute('INSERT INTO videos (title, url) VALUES (?, ?)', (title, url))
		conn.commit()

def update_video_in_db(video_id, field, new_value):
	with sqlite3.connect(DB_NAME) as conn:
		cursor = conn.cursor()
		if field == "title":
			cursor.execute('UPDATE videos SET title = ? WHERE id = ?', (new_value, video_id))
		elif field == "url":
			cursor.execute('UPDATE videos SET url = ? WHERE id = ?', (new_value, video_id))
		conn.commit()

def delete_video_from_db(video_id):
	with sqlite3.connect(DB_NAME) as conn:
		cursor = conn.cursor()
		cursor.execute('DELETE FROM videos WHERE id = ?', (video_id,))
		conn.commit()

# =====================================================================
# UTILITY HELPER FUNCTIONS
# =====================================================================

def get_youtube_title(url):
	if not url.startswith(('http://', 'https://')):
		url = 'https://' + url
	try:
		oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
		response = requests.get(oembed_url, timeout=10)
		if response.status_code == 200:
			data = response.json()
			return data.get('title')
	except requests.exceptions.RequestException:
		pass
	return None

def clear_screen():
	os.system('cls' if os.name == 'nt' else 'clear')

def download_video_apify(url):
	if not APIFY_TOKEN or APIFY_TOKEN == "APIFY_API_TOKEN":
		print("First set the Apify API Token in your .env file.")
		return
	
	print("Connecting to Apify Cloud Platform....")
	apify_client = ApifyClient(APIFY_TOKEN)
	run_input = {
		"videos": [{
			"url": url
		}]
	}

	try:
		print("Running the downloader actor in Apify Cloud Platform....")
		# Increased memory to 1024MB to prevent the download from getting cut off mid-way.
		run = apify_client.actor("streamers/youtube-video-downloader").call(run_input=run_input, memory_mbytes=1024)
		 
		print("Fetching download data from the dataset...")
		
		# Safely extract the dataset ID. 
		# Handles both dicts (modern client) and objects (older versions/SDK).
		dataset_id = run.get("defaultDatasetId") if isinstance(run, dict) else \
                     getattr(run, "default_dataset_id", getattr(run, "defaultDatasetId", None))

		link_found = False
		dataset_items = list(apify_client.dataset(dataset_id).iterate_items())

		for item in dataset_items:
			# Try multiple common fields for the download URL
			download_url = (
				item.get("downloadUrl") or 
				item.get("downloadedFileUrl") or 
				item.get("videoUrl") or 
				item.get("videoOnlyUrl") or 
				item.get("fileUrl")
			)
			
			# Fallback: check if 'url' is present and is NOT the original YouTube link
			if not download_url:
				candidate_url = item.get("url")
				if candidate_url and "youtube.com" not in candidate_url and "youtu.be" not in candidate_url:
					download_url = candidate_url

			if download_url:
				print(f"\n🎉 Success! Download link generated.")
				print(f"🔗 Link: {download_url}")
				link_found = True

				print("🍿 Launching your browser to fetch the file...")
				webbrowser.open(download_url)
				break

		if not link_found:
			print("\n❌ Error: Could not extract a direct download URL from the response.")
			if not dataset_items:
				print("⚠️ The result dataset is empty. This usually means the actor failed to process the video.")
			else:
				print(f"DEBUG: Found {len(dataset_items)} items, but none contained a valid download link.")
				print(f"Available keys in first result: {list(dataset_items[0].keys())}")
			print(f"💾 Check your run console for details: https://console.apify.com/storage/datasets/{dataset_id}")

	except Exception as e:
		print(f"\n⚠️ Something went wrong during API call. Error:{e}")

def display_video_list(videos):
	if not videos:
		print("No videos found in your manager. Add some videos first!")
		return False
	print("\n"+"*" * 90,"\n")
	print(f"{'Index':<6} | {'Video Title':<50} | {'Video URL'}")
	print('-' * 90)
	for index, (db_id, title, url) in enumerate(videos, start=1):
		short_title = title[:47] + '...' if len(title) > 50 else title
		print(f"{index:<6} | {short_title:<50} | {url}")
	print("\n"+"=" * 90,"\n")
	return True
		
def get_valid_index(videos,prompt_txt):
	while True:
		user_input = input(prompt_txt).strip()
		if user_input.lower() == "n":
			return 'back'
		try:
			index = int(user_input) - 1
			if 0 <= index < len(videos):
				return index
			else:
				print("Invalid video index. Please try again.")
		except ValueError:
			print("Invalid input. Please enter a valid video index or 'n' to go back.")

# =====================================================================
# CORE FEATURES
# =====================================================================

def watch_video():
	clear_screen()
	videos = fetch_all_videos()
	if not display_video_list(videos):
		return
	
	choice = get_valid_index(videos,"Enter the index no. to watch (or n to go back):")
	if choice != 'back':
		webbrowser.open(videos[choice][2])
		print(f"Opening: {videos[choice][1]}...")
	else:
		print("Returning to the main menu...")
		return
	
def add_video():
	clear_screen()
	print("--- ➕ Add New Video ---")
	url = input("Enter the YouTube video URL: ").strip()
	if not url:
		print("Invalid URL. Please try again.")
		return
	print("Fetching video details...")
	title = get_youtube_title(url)

	if title:
		print(f"Found video title: {title}")
		confirm = input("Keep this title? (y/n): ").lower()
		if confirm != 'y':
			title = input("Enter the video title: ")	
	else:
		title = input("Failed to retrieve video title. Enter the video title manually: ")
		
	if title:
		add_video_to_db(title,url)
		print("Video added successfully!")
	else:
		print("Video not added. Title cannot be empty.")

def update_video():
	clear_screen()
	print("--- ✏️ Update Video Details ---")
	videos = fetch_all_videos()
	if not display_video_list(videos):
		return
	
	choice = get_valid_index(videos,"Enter the index no. to update (or n to go back):")
	if choice == 'back':
		print("Returning to the main menu...")
		return
	
	video_id = videos[choice][0]
	print(f"Selected video: {videos[choice][1]}")
	print("What would you like to update?")
	print("1. Title")
	print("2. URL")
	
	update_choice = input("Enter your choice (1-2): ")
	if update_choice == '1':
		new_title = input("Enter the new title: ")
		if new_title:
			update_video_in_db(video_id, "title", new_title)
			print("Title updated successfully!")
		else:
			print("Title cannot be empty.")
	elif update_choice == '2':
		new_url = input("Enter the new URL: ")
		if new_url:
			update_video_in_db(video_id, "url", new_url)
			print("URL updated successfully!")
		else:
			print("URL cannot be empty.")
	else:
		print("Invalid choice. Please try again.")

def delete_video():
	clear_screen()
	print("--- 🗑️ Delete Video ---")
	videos = fetch_all_videos()
	if not display_video_list(videos):
		return
	
	choice = get_valid_index(videos,"Enter the index no. to delete (or n to go back):")

	if choice == 'back':
		print("Returning to the main menu...")
		return
	
	video_id = videos[choice][0]
	print(f"Selected video: {videos[choice][1]}")
	confirm = input("Are you sure you want to delete this video? (y/n): ").lower()
	if confirm == 'y':
		delete_video_from_db(video_id)
		print("Video deleted successfully!")
	else:
		print("Video not deleted.")

def download_video():
	clear_screen()
	print("--- 📥 Download Video ---")
	videos = fetch_all_videos()
	
	while True:
		print("Enter the option which you wanna go for:")
		print("1. Download from the list of saved videos.")
		print("2. Insert custom URL.")
		print("3. Go back.")

		choice = input("Enter your choice (1-3): ")
		match choice:
			case "1":
				if not display_video_list(videos):
					return
				choice = get_valid_index(videos,"Enter the index no. to download (or n to go back):")
				if choice != 'back':
					download_video_apify(videos[choice][2])
				else:
					print("Returning to the main menu...")
			case "2":
				url = input("Enter the YouTube video URL: ").strip()
				if url:
					download_video_apify(url)
				else:
					print("Invalid URL.")
			case "3":
				return
			case _:
				print("Invalid choice. Please try again.")
				continue
	

# =================================================
# MAIN FUNCTION
# =================================================

def main():
	init_db()
	while True:
		print("\n📺 === YOUTUBE VIDEO MANAGER (SQLite) ===")
		print("What would you like to do?")
		print("1. Watch / Open Video")
		print("2. Add New Video")
		print("3. Update Video Details")
		print("4. Download Video")
		print("5. Delete Video")
		print("6. Exit Application")
	
		choice = input("Enter your choice (1-6): ")

		match choice:
			case "1": watch_video()
			case "2": add_video()
			case "3": update_video()
			case "4": download_video()
			case "5": delete_video()
			case "6":
				clear_screen()
				print("\n Thanks for using Youtube Video Manager")
				break 
			case _:
				print("Invalid choice. Please try again.")

		input("\nPress Enter to return to the main menu...")
		clear_screen()

if __name__ == "__main__":
	main()