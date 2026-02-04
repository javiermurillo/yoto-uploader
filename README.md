# Yoto Audio Uploader

This script automates the process of uploading audio files to the Yoto "My Cards" platform. It is specifically designed for personal use to easily upload audiobooks and music for your child's cards.

## Features

- **Batch Upload:** Uploads files in chunks of 3 to avoid overwhelming the platform.
- **Format Support:** Supports `.mp3`, `.m4a`, `.wav`, and `.m4b`.
- **Robustness:** Uses direct file input methods to avoid UI stability issues.
- **Playlist Management:**
  - Asks for the **Playlist Name** at the start.
  - Automatically fills in the name.
  - **Manual Save:** Pauses at the end so you can verify everything and click "Create" yourself.
- **Random Icons:** Automatically cycles through every uploaded track and assigns a **random icon** to it, so you don't have to set them manually!

## Requirements

1.  **Python 3.12+**
2.  **Playwright:** Required for browser automation.

## Installation

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Install Playwright browsers:
    ```bash
    playwright install chromium
    ```
3.  Configure your credentials:
    - Copy the example environment file: `cp .env.example .env`
    - Edit `.env` and enter your Yoto email and password.

## Usage

The process is split into two steps to ensure your files are saved safely.

### Step 1: Upload & Create

1.  Run the script without arguments:
    ```bash
    python yoto_uploader.py
    ```
2.  Enter the **Playlist Name** and **Audio Folder**.
3.  The browser will upload your files.
4.  **Important:** Wait for uploads to finish, then click **Create** manually in the browser to save the playlist.
5.  **Copy the URL** of the new playlist (e.g., `https://my.yotoplay.com/card/xxxxx/edit`) and press Enter to close.

### Step 2: Assign Random Icons

1.  Run the script providing the Playlist URL:
    ```bash
    python yoto_uploader.py "https://my.yotoplay.com/card/xxxxx/edit"
    ```
2.  The script will log in, navigate to that playlist, and assign unique random icons to all tracks.
3.  Once done, click **Update** (or Save) manually.

## Important Notes

- This script is for **personal use**.
- If the Yoto platform updates its UI, this script might need adjustments (e.g., selectors for icons or buttons).
