import sqlite3
import webbrowser
import requests
import os

DB_NAME = "videos.db"

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
		print("4. Delete Video")
		print("5. Exit Application")
	
		choice = input("Enter your choice (1-5): ")

		match choice:
			case "1": watch_video()
			case "2": add_video()
			case "3": update_video()
			case "4": delete_video()
			case "5":
				clear_screen()
				print("\n Thanks for using Youtube Video Manager")
				break 
			case _:
				print("Invalid choice. Please try again.")

		input("\nPress Enter to return to the main menu...")
		clear_screen()

if __name__ == "__main__":
	main()