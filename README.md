# YouTube Video Manager DB

A simple and elegant Command Line Interface (CLI) application in Python to manage your favorite YouTube videos. It uses a lightweight SQLite database to store your video links and titles, allowing you to quickly add, update, delete, and watch videos right from your terminal.

## 🌟 Features

- **Add New Videos**: Add a YouTube URL and automatically fetch its title, or provide your own title.
- **Watch Videos**: Open any saved video directly in your default web browser from the CLI.
- **Update Details**: Easily update a video's title or URL if it changes.
- **Download Videos**: Integration with the Apify Cloud Platform to generate direct download links for videos.
- **Delete Videos**: Remove videos from your collection when you no longer need them.
- **Persistent Storage**: All video data is safely stored locally in an SQLite database (`videos.db`).

## 🛠️ Prerequisites

- **Python 3.10+**: The application utilizes Python's `match-case` structural pattern matching.
- **`requests` library**: Used for fetching YouTube video titles automatically via the oEmbed API.

## 🚀 Installation & Setup

1. **Clone the repository or download the project files:**
   ```bash
   git clone <your-repo-url>
   cd "Youtube Manager db"
   ```

2. **Install the required dependencies:**
   Install the `requests` library using `pip`:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Environment Variables:**
   Create a `.env` file in the root directory and add your Apify API Token:
   ```text
   APIFY_TOKEN=your_apify_api_token_here
   ```

4. **Run the Application:**
   Navigate to the `src` directory and run the script:
   ```bash
   cd src
   python app.py
   ```

## 🎮 Usage

When you run the application, you will be greeted with the main menu:

```text
📺 === YOUTUBE VIDEO MANAGER (SQLite) ===
What would you like to do?
1. Watch / Open Video
2. Add New Video
3. Update Video Details
4. Download Video
5. Delete Video
6. Exit Application
```

Simply type the number corresponding to your choice and press **Enter**.

- **Adding a Video**: Just paste the YouTube URL, and the tool will automatically attempt to fetch the video's title. You can choose to keep it or manually enter a different one.
- **Watching a Video**: Select option 1, then enter the index of the video you want to watch. It will open automatically in your browser using Python's built-in `webbrowser` module.

## 🗄️ Database

The application automatically creates an SQLite database named `videos.db` in the same directory as the execution path upon its first run. The database schema stores:
- An auto-incrementing integer `id`
- The video `title` (Text)
- The video `url` (Text)
