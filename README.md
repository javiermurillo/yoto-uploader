# Yoto Audio Uploader

CLI helper script to automate uploading audio files to the **Yoto "My Cards"** platform. It is designed for personal use (your own Yoto account) and is now structured so the community can run, extend, and contribute safely.

> ⚠️ This is **not** an official Yoto tool. Use at your own risk and always respect Yoto's Terms of Service.

## What it does

- **Batch upload** audio files to a new playlist ("My Cards")
- **Chunked uploads** (default: groups of 3 files) to avoid overloading the UI
- Supports `.mp3`, `.m4a`, `.wav`, `.m4b`
- Uses Playwright to automate Chromium
- Optional second phase that assigns **random icons** to each track

All critical actions (creating / saving playlists) are still confirmed manually by you in the browser.

## Requirements

- Python **3.12+**
- [Playwright](https://playwright.dev/) (installed via `pip` + `playwright install`)
- A Yoto account with access to **My Cards**

## Installation

Clone the repo and install dependencies:

```bash
git clone https://github.com/javiermurillo/yoto-uploader.git
cd yoto-uploader

pip install -r requirements.txt
playwright install chromium
```

### Configure credentials

Create your `.env` from the example:

```bash
cp .env.example .env
```

Then edit `.env` and set:

```bash
YOTO_EMAIL=you@example.com
YOTO_PASSWORD=your-password-here
```

These values are **not** committed thanks to `.gitignore`.

## Usage

The script supports two modes:

1. **Upload Mode** – create a new playlist and upload all tracks.
2. **Icon Mode** – given an existing playlist URL, randomize the icons for all tracks.

### 1. Upload Mode (new playlist)

```bash
python yoto_uploader.py
```

You will be asked for:

- **Playlist name** (e.g. `Matilda – Audiobook`)
- **Path to audio folder** (e.g. `/Users/you/Audiobooks/Matilda`)

Flow:

1. Script logs in to your Yoto account (using credentials from `.env` or from prompts).
2. Opens the playlist editor: `https://my.yotoplay.com/card/edit`.
3. Fills in the playlist name.
4. Uploads audio files in **chunks of 3**.
5. Waits for server-side processing to finish (based on the **Create** button becoming enabled).
6. Stops and gives you instructions to **manually click "Create"** to save the playlist.

You then copy the URL of the edit page (something like `https://my.yotoplay.com/card/XXXXX/edit`) for the next step if you want icons.

### 2. Icon Mode (random icons)

Once you have an existing playlist URL, run:

```bash
python yoto_uploader.py "https://my.yotoplay.com/card/XXXXX/edit"
```

The script will:

1. Log in again (same credentials).
2. Navigate to the edit URL.
3. Wait until processing is complete.
4. Iterate over each track and open the icon picker dialog.
5. Assign a **unique random icon** per track (re-using icons only if it runs out).
6. Give you time to verify and manually click **Update/Save**.

## Development & Contributing

Contributions are welcome. Some ideas:

- Add CLI flags (e.g. `--chunk-size`, `--headless`, `--skip-icons`).
- Improve resilience to Yoto UI changes (selectors, retries, better progress handling).
- Add tests for helper functions (`get_valid_audio_files`, chunking, etc.).

### Project structure

```bash
yoto-uploader/
  README.md
  LICENSE
  requirements.txt
  yoto_uploader.py
  .env.example
  .gitignore
```

### Running locally

```bash
python yoto_uploader.py                    # upload mode
python yoto_uploader.py "<playlist-url>"   # icon mode
```

## Safety & Terms

- This tool uses browser automation (Playwright) to control your own Yoto session.
- You are responsible for how you use it; do not spam or violate Yoto's Terms of Service.
- If Yoto changes their UI, selectors may break and require an update.

## License

This project is licensed under the **MIT License**. See [`LICENSE`](./LICENSE).
