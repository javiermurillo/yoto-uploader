# Yoto Audio Uploader

This script automates the process of uploading audio files to the Yoto "My Cards" platform. It is specifically designed for personal use to easily upload audiobooks and music for your child's cards.

## Features

- **Batch Upload:** Uploads files in chunks of 3 to avoid overwhelming the platform.
- **Format Support:** Supports `.mp3`, `.m4a`, `.wav`, and `.m4b`.
- **Robustness:** Uses direct file input methods to avoid UI stability issues.
- **Playlist Management:**
  - Asks for the **Playlist Name** at the start.
  - Automatically fills in the name.
  - Automatically clicks "Create" to **save** the playlist at the end.
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

1.  Run the script:
    ```bash
    python yoto_uploader.py
    ```
2.  When prompted, enter:
    - The **Name** you want for the Playlist.
    - The **Full Path** to the folder containing your audio files.
3.  The browser will open (do not close it).
    - It will log in, navigate to the editor, and start uploading.
    - Once uploads are done, it will automatically assign random icons to each track.
    - Finally, it will click "Create" to save.

## Important Notes

- This script is for **personal use**.
- If the Yoto platform updates its UI, this script might need adjustments (e.g., selectors for icons or buttons).
