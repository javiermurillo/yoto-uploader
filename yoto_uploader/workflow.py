"""Core high-level workflows for Yoto uploader.

This module contains the upload and icon-randomization flows that operate
on a Playwright Page instance. It uses 'rich' for progress reporting.
"""

import sys
import time
from typing import Optional

from playwright.sync_api import Page, sync_playwright
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

from .auth import get_credentials
from .files import chunk_list, get_valid_audio_files


# ------------------- Low-level helpers -------------------


def upload_chunk(page: Page, chunk_files, chunk_index: int) -> None:
    """Handle the upload of a single chunk of files."""
    from pathlib import Path

    file_paths = [str(Path(f).absolute()) for f in chunk_files]

    try:
        page.set_input_files("#upload", file_paths)
    except Exception:  # noqa: BLE001
        # Fallback if direct input fails
        with page.expect_file_chooser() as fc_info:
            page.click("label:has-text('Add audio')")
        file_chooser = fc_info.value
        file_chooser.set_files(file_paths)

    # Wait a bit for the upload to actually register/start in the UI
    time.sleep(10)


def wait_and_create(page: Page, playlist_name: str, timeout: int = 600) -> str:
    """Wait for processing to finish, click Create, and retrieve the new playlist ID.

    Since Yoto redirects to the library page instead of the edit page, we intercept
    the API call to `/content/mine` to find our new playlist ID.
    """
    start_time = time.time()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task("Processing tracks...", total=None)

        while time.time() - start_time < timeout:
            # Check if Create button is enabled
            if page.is_enabled("button.create-btn"):
                progress.update(task, description="Processing complete. Creating playlist...")
                
                # Setup response listener BEFORE clicking
                # We want to catch the response that lists all cards
                with page.expect_response("**/content/mine", timeout=60000) as response_info:
                    page.click("button.create-btn", force=True)
                
                progress.update(task, description="Waiting for playlist data...")
                
                # Get the JSON from the intercepted response
                response = response_info.value
                if not response.ok:
                    raise RuntimeError(f"API request failed: {response.status} {response.url}")
                
                data = response.json()
                # The API returns {"cards": [...]}
                cards = data if isinstance(data, list) else data.get("cards", [])

                # Find our card by TITLE (not name)
                target_card = next(
                    (c for c in cards if c.get("title", "").strip() == playlist_name.strip()), 
                    None
                )

                if target_card:
                    card_id = target_card.get("cardId")  # It is 'cardId', not 'id' based on the JSON sample
                    if card_id:
                        progress.stop()
                        return f"https://my.yotoplay.com/card/{card_id}/edit"
                
                progress.stop()
                print(f"Warning: Could not find card named '{playlist_name}' in API response.")
                return "https://my.yotoplay.com/my-cards"

            # Heuristic check for status text
            try:
                content = page.content().lower()
                if any(w in content for w in ("processing", "transcoding", "analyzing")):
                    progress.update(task, description="Server is transcoding/processing...")
            except Exception:
                pass

            time.sleep(2)

    raise TimeoutError("Timed out waiting for processing to complete.")


def randomize_icons(page: Page) -> None:
    """Assign a random unique icon to each uploaded track."""
    import random

    try:
        cookie_btn = page.locator("button.cky-btn-accept").first
        if cookie_btn.is_visible():
            cookie_btn.click()
            time.sleep(1)
    except Exception:
        pass

    try:
        page.wait_for_selector("img.trackIcon[alt='Choose icon']", timeout=10000)
    except Exception:
        print("Warning: No icons found to update.")
        return

    icon_locator = page.locator("img.trackIcon[alt='Choose icon']")
    count = icon_locator.count()
    
    used_icon_srcs = set()

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        task = progress.add_task("Randomizing icons...", total=count)

        for i in range(count):
            if "/edit" not in page.url:
                print(f"Error: Navigated away from editor! URL: {page.url}")
                break

            progress.update(task, advance=0, description=f"Icon {i+1}/{count}")

            try:
                # 1. Open dialog
                icon = icon_locator.nth(i)
                icon.scroll_into_view_if_needed()
                page.evaluate("window.scrollBy(0, -150)")
                time.sleep(0.5)

                try:
                    icon.click(timeout=5000)
                except Exception:
                    icon.click(force=True)

                target_dialog = "div[role='dialog']:has(img.trackIcon)"
                page.wait_for_selector(target_dialog, state="visible", timeout=5000)

                # 2. Pick icon
                dialog_icons_sel = f"{target_dialog} img.trackIcon"
                page.wait_for_selector(dialog_icons_sel, timeout=5000)
                
                available = page.query_selector_all(dialog_icons_sel)
                if available:
                    valid_opts = [
                        (ico, ico.get_attribute("src")) 
                        for ico in available 
                        if ico.get_attribute("src") not in used_icon_srcs
                    ]
                    
                    # Recycle if exhausted
                    if not valid_opts:
                        used_icon_srcs.clear()
                        valid_opts = [
                            (ico, ico.get_attribute("src")) for ico in available
                        ]

                    chosen_el, chosen_src = random.choice(valid_opts)
                    if chosen_src:
                        used_icon_srcs.add(chosen_src)
                    
                    chosen_el.click(force=True)
                    page.wait_for_selector(target_dialog, state="hidden", timeout=5000)
                else:
                    page.keyboard.press("Escape")

                time.sleep(1.0) # Short pause between icons
                progress.update(task, advance=1)

            except Exception as e:
                print(f"Failed to update icon {i+1}: {e}")
                # Try recovery
                try:
                    if page.is_visible("div[role='dialog']:has(img.trackIcon)"):
                        page.keyboard.press("Escape")
                except Exception:
                    pass


# ------------------- High-level workflows -------------------


def run_upload_mode(page: Page, email: str, password: str, *, chunk_size: int = 3) -> None:
    """Upload mode: create a new playlist and upload all tracks."""
    
    from playwright.sync_api import TimeoutError as PlaywrightTimeout

    print("\n=== UPLOAD MODE ===")
    
    # Inputs (interactive for now)
    playlist_name = input("Enter playlist name: ").strip()
    while not playlist_name:
        playlist_name = input("Enter playlist name: ").strip()

    folder_input = input("Enter path to audio folder: ").strip()
    folder_input = folder_input.replace("'", "").replace('"', "")
    
    try:
        audio_files = get_valid_audio_files(folder_input)
    except FileNotFoundError:
        print(f"Error: Folder not found: {folder_input}")
        return

    if not audio_files:
        print("No valid audio files found.")
        return

    chunks = list(chunk_list(audio_files, chunk_size))
    
    # Login
    print("Logging in...")
    page.goto("https://us.yotoplay.com/my-account")
    page.fill("input[name='username']", email)
    page.fill("input[name='password']", password)
    page.click("button[type='submit']")
    
    try:
        page.wait_for_url("**/my-account", timeout=60000)
    except PlaywrightTimeout:
        print("\n⚠️  Login taking too long. If CAPTCHA appeared, solve it (requires visible mode).")
        return

    print("Navigating to Playlist Editor...")
    page.goto("https://my.yotoplay.com/card/edit")
    
    print(f"Setting playlist name: {playlist_name}")
    page.fill("input[placeholder='Playlist name']", playlist_name)
    
    # Upload loop with progress
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total} chunks"),
    ) as progress:
        task = progress.add_task("Uploading chunks...", total=len(chunks))
        
        for i, chunk in enumerate(chunks, 1):
            progress.update(task, description=f"Uploading chunk {i}/{len(chunks)}")
            upload_chunk(page, chunk, i)
            progress.update(task, advance=1)

    # Wait and Auto-Create
    created_url = wait_and_create(page, playlist_name)
    print(f"\n✅ Playlist created successfully!")
    print(f"Edit URL: {created_url}")
    print("You can use this URL to run the 'icons' command if you want to randomize icons later.")


def run_icon_mode(page: Page, email: str, password: str, edit_url: str) -> None:
    """Icon mode: assign random icons to an existing playlist URL."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeout

    print("\n=== ICON MODE ===")
    print(f"Target URL: {edit_url}")
    
    print("Logging in...")
    page.goto("https://us.yotoplay.com/my-account")
    page.fill("input[name='username']", email)
    page.fill("input[name='password']", password)
    page.click("button[type='submit']")
    
    try:
        page.wait_for_url("**/my-account", timeout=60000)
    except PlaywrightTimeout:
        print("Login failed or timed out.")
        return

    print(f"Navigating to: {edit_url}")
    page.goto(edit_url)
    
    # Randomize
    randomize_icons(page)
    
    # Save changes
    print("Saving changes...")
    if page.is_enabled("button.create-btn"): # It might be "Update" or same selector
        page.click("button.create-btn")
        page.wait_for_load_state("networkidle")
    
    print("\n✅ Icons updated.")


def run_playwright(
    *,
    target_url: Optional[str] = None,
    chunk_size: int = 3,
    headless: bool = True,  # Default to TRUE (headless)
) -> None:
    """Entry point that bootstraps Playwright."""
    
    email, password = get_credentials()

    with sync_playwright() as p:
        print(f"Launching browser (Headless: {headless})...")
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        try:
            if target_url:
                run_icon_mode(page, email, password, target_url)
            else:
                run_upload_mode(page, email, password, chunk_size=chunk_size)
        finally:
            browser.close()


def main() -> None:
    """Legacy entry point."""
    target_url = sys.argv[1] if len(sys.argv) > 1 else None
    # For legacy script usage, we default to VISIBLE to match old behavior?
    # Or match new default? Let's match new default (headless) but maybe print a note.
    run_playwright(target_url=target_url, headless=True)
