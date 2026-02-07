"""Core high-level workflows for Yoto uploader.

This module contains the upload and icon-randomization flows that operate
on a Playwright Page instance. It is intentionally kept free of CLI/argparse
logic so it can be reused programmatically or wrapped by different CLIs.
"""

import sys
import time
from typing import List, Optional

from playwright.sync_api import Page, sync_playwright

from .auth import get_credentials
from .files import chunk_list, get_valid_audio_files


# ------------------- Low-level helpers -------------------


def upload_chunk(page: Page, chunk_files, chunk_index: int, total_chunks: int) -> None:
    """Handle the upload of a single chunk of files.

    This is mostly a thin wrapper around the existing logic.
    """

    from pathlib import Path

    print(f"Uploading chunk {chunk_index} of {total_chunks}...")

    file_paths = [str(Path(f).absolute()) for f in chunk_files]

    try:
        page.set_input_files("#upload", file_paths)
    except Exception as e:  # noqa: BLE001
        print(f"  -> Error uploading files directly: {e}")
        print("  -> Attempting alternative method (Click)...")
        with page.expect_file_chooser() as fc_info:
            page.click("label:has-text('Add audio')")
        file_chooser = fc_info.value
        file_chooser.set_files(file_paths)

    print(f"  -> Waiting for chunk {chunk_index} processing...")
    time.sleep(10)
    print(f"  -> Chunk {chunk_index} completed (Wait time finished).")


def wait_for_processing(page: Page, timeout: int = 600) -> None:
    """Wait for the Create button to be enabled, up to ``timeout`` seconds."""

    print("\n--- Verifying processing status ---")
    start_time = time.time()

    while time.time() - start_time < timeout:
        if page.is_enabled("button.create-btn"):
            print("  -> Processing complete (Create button enabled).")
            return

        elapsed = int(time.time() - start_time)
        print(f"  -> Waiting for processing to finish... ({elapsed}s)")

        try:
            content = page.content().lower()
            if any(w in content for w in ("processing", "transcoding", "analyzing")):
                print("     (Status text detected: Processing/Analyzing...)")
        except Exception:  # noqa: BLE001
            pass

        time.sleep(5)

    print("Warning: Timeout reached. Attempting to proceed anyway...")


def randomize_icons(page: Page) -> None:
    """Assign a random unique icon to each uploaded track."""

    import random

    print("\n--- Assigning unique random icons ---")

    try:
        cookie_btn = page.locator("button.cky-btn-accept").first
        if cookie_btn.is_visible():
            print("  -> Dismissing Cookie Banner...")
            cookie_btn.click()
            time.sleep(1)
    except Exception:  # noqa: BLE001
        pass

    try:
        page.wait_for_selector("img.trackIcon[alt='Choose icon']", timeout=10000)
    except Exception:  # noqa: BLE001
        print("warning: No icons found to update.")
        return

    icon_locator = page.locator("img.trackIcon[alt='Choose icon']")
    count = icon_locator.count()
    print(f"Found {count} tracks to update.")

    used_icon_srcs = set()

    for i in range(count):
        if "/edit" not in page.url:
            print(f"    -> Error: Navigated away from editor! Current URL: {page.url}")
            print("    -> Stopping icon randomization.")
            break

        try:
            print(f"  -> Updating icon for track {i+1}...")
            icon = icon_locator.nth(i)
            icon.scroll_into_view_if_needed()
            page.evaluate("window.scrollBy(0, -150)")
            time.sleep(0.5)

            try:
                icon.click(timeout=5000)
            except Exception:
                print("      -> Standard click failed, trying force click...")
                icon.click(force=True)

            target_dialog_selector = "div[role='dialog']:has(img.trackIcon)"
            page.wait_for_selector(target_dialog_selector, state="visible", timeout=5000)

            dialog_icons_selector = f"{target_dialog_selector} img.trackIcon"
            page.wait_for_selector(dialog_icons_selector, timeout=5000)

            available_icons = page.query_selector_all(dialog_icons_selector)
            if available_icons:
                valid_options = []
                for ico in available_icons:
                    src = ico.get_attribute("src")
                    if src and src not in used_icon_srcs:
                        valid_options.append((ico, src))

                if not valid_options:
                    used_icon_srcs.clear()
                    valid_options = [
                        (ico, ico.get_attribute("src")) for ico in available_icons
                    ]

                chosen_icon_element, chosen_src = random.choice(valid_options)
                if chosen_src:
                    used_icon_srcs.add(chosen_src)

                chosen_icon_element.click(force=True)
                page.wait_for_selector(target_dialog_selector, state="hidden", timeout=5000)
            else:
                print("    -> No icons found in dialog, pressing Escape.")
                page.keyboard.press("Escape")

            print("    -> Waiting 3s for stability...")
            time.sleep(3.0)

        except Exception as e:  # noqa: BLE001
            print(f"    -> Failed to update icon {i+1}: {e}")
            try:
                diag_selector = "div[role='dialog']:has(img.trackIcon)"
                if page.is_visible(diag_selector):
                    print("    -> Dialog appeared stuck open. Closing with Escape.")
                    page.keyboard.press("Escape")
                    page.wait_for_selector(diag_selector, state="hidden", timeout=3000)
                else:
                    print(
                        "    -> Dialog not visible. Skipping Escape to avoid accidental navigation.",
                    )
            except Exception as e2:  # noqa: BLE001
                print(f"    -> Error attempting to recover: {e2}")


# ------------------- High-level workflows -------------------


def run_upload_mode(page: Page, email: str, password: str, *, chunk_size: int = 3) -> None:
    """Upload mode: create a new playlist and upload all tracks."""

    from playwright.sync_api import TimeoutError as PlaywrightTimeout

    print("\n=== UPLOAD MODE ===")

    playlist_name = input("Enter playlist name: ").strip()
    while not playlist_name:
        print("Playlist name cannot be empty.")
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
    total_chunks = len(chunks)

    print("Logging in...")
    page.goto("https://us.yotoplay.com/my-account")
    page.fill("input[name='username']", email)
    page.fill("input[name='password']", password)
    page.click("button[type='submit']")

    print("Waiting for login...")
    try:
        page.wait_for_url("**/my-account", timeout=60000)
    except PlaywrightTimeout:
        print("\n⚠️  Login seems to be taking a while or CAPTCHA appeared.")
        input("    Press Enter in this terminal once you have logged in successfully...")

    print("Navigating to Playlist Editor...")
    page.goto("https://my.yotoplay.com/card/edit")

    print(f"Setting playlist name: {playlist_name}")
    page.fill("input[placeholder='Playlist name']", playlist_name)

    for i, chunk in enumerate(chunks, 1):
        upload_chunk(page, chunk, i, total_chunks)

    wait_for_processing(page)

    print("\n--- UPLOAD COMPLETED ---")
    print("Files have been uploaded. Please:")
    print("1. Verify there are no loading spinners.")
    print("2. Click 'Create' manually to save the playlist.")
    print("3. Once saved, copy the URL of the edit page (something like .../card/XXXX/edit) to use in icon mode.")

    input("\nPress Enter to finish and close the browser...")


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

    print("Waiting for login...")
    try:
        page.wait_for_url("**/my-account", timeout=60000)
    except PlaywrightTimeout:
        print("\n⚠️  Login seems to be taking a while or CAPTCHA appeared.")
        input("    Press Enter in this terminal once you have logged in successfully...")

    print(f"Navigating to: {edit_url}")
    page.goto(edit_url)

    wait_for_processing(page)
    randomize_icons(page)

    print("\n--- ASSIGNMENT COMPLETED ---")
    print("Verify icons and click 'Update/Save' if necessary.")
    input("\nPress Enter to close...")


def run_playwright(  # pragma: no cover - Playwright glue is hard to unit-test
    *,
    target_url: Optional[str] = None,
    chunk_size: int = 3,
    headless: bool = False,
) -> None:
    """Entry point that bootstraps Playwright and runs the chosen workflow."""

    email, password = get_credentials()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        if target_url:
            run_icon_mode(page, email, password, target_url)
        else:
            run_upload_mode(page, email, password, chunk_size=chunk_size)

        browser.close()


def main() -> None:  # pragma: no cover - preserved for backwards compatibility
    """Legacy entry point used when running `python yoto_uploader.py` directly.

    This preserves the old behavior while the new CLI is layered on top.
    """

    target_url = sys.argv[1] if len(sys.argv) > 1 else None
    run_playwright(target_url=target_url)
