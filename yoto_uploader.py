import os
import time
import math
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page, expect

# Load environment variables
load_dotenv()

def get_credentials():
    """Retrieve credentials from env or prompt user."""
    email = os.getenv("YOTO_EMAIL")
    password = os.getenv("YOTO_PASSWORD")
    
    if not email:
        email = input("Enter Yoto Email: ")
    if not password:
        password = input("Enter Yoto Password: ")
    
    return email, password

def get_valid_audio_files(folder_path: str) -> list[Path]:
    """Scan folder for audio files, filter, and sort alphabetically."""
    path = Path(folder_path)
    if not path.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    
    valid_extensions = {'.mp3', '.m4a', '.wav', '.m4b'}
    files = [
        f for f in path.iterdir() 
        if f.is_file() and f.suffix.lower() in valid_extensions
    ]
    files.sort(key=lambda x: x.name)
    return files

def chunk_list(data, size):
    """Yield successive n-sized chunks from data."""
    for i in range(0, len(data), size):
        yield data[i:i + size]

def upload_chunk(page: Page, chunk_files: list[Path], chunk_index: int, total_chunks: int):
    """Handles the upload of a single chunk of files."""
    print(f"Uploading chunk {chunk_index} of {total_chunks}...")
    
    file_paths = [str(f.absolute()) for f in chunk_files]
    
    # robust approach: target the hidden input directly
    # This avoids the instability of clicking the label and waiting for the file chooser
    try:
        page.set_input_files("#upload", file_paths)
    except Exception as e:
        print(f"  -> Error uploading files directly: {e}")
        print("  -> Attempting alternative method (Click)...")
        with page.expect_file_chooser() as fc_info:
            page.click("label:has-text('Add audio')")
        file_chooser = fc_info.value
        file_chooser.set_files(file_paths)

    # --- LOGIC CORE: Wait for upload completion ---
    print(f"  -> Waiting for chunk {chunk_index} processing...")
    
    # Validation relaxation: File names often change/shorten on the platform.
    # Instead of strict name checking, we rely on a generous wait and visual progress.
    # We wait a bit longer to be safe since we removed the strict check.
    time.sleep(10) 
    
    print(f"  -> Chunk {chunk_index} completed (Wait time finished).")

def wait_for_processing(page: Page, timeout: int = 600):
    """
    Waits for the 'Create' button to be enabled, which indicates that 
    server-side processing (transcoding/analysis) is complete.
    """
    print("\n--- Verifying processing status ---")
    start_time = time.time()
    
    # We poll every few seconds
    while time.time() - start_time < timeout:
        # Check if the Create button is enabled
        # The selector is button.create-btn
        if page.is_enabled("button.create-btn"):
            print("  -> Processing complete (Create button enabled).")
            return
        
        elapsed = int(time.time() - start_time)
        print(f"  -> Waiting for processing to finish... ({elapsed}s)")
        
        # Optional: Try to identify any "Processing" text to show status
        # We assume common terms like "Processing", "Transcoding", "Analysing" might be visible
        try:
            # Quick check for typical status text (case insensitive search via regex could be better but heavy)
            content = page.content().lower()
            if "processing" in content or "transcoding" in content or "analyzing" in content:
                print("     (Status text detected: Processing/Analyzing...)")
        except:
            pass

        time.sleep(5)
    
    print("Warning: Timeout reached. Attempting to proceed anyway...")

def randomize_icons(page: Page):
    """Assigns a random unique icon to each uploaded track."""
    print("\n--- Assigning unique random icons ---")
    import random
    
    # 0. Dismiss Cookie Banner if present (it interferes with dialog detection)
    try:
        # Common selector for cookie acceptance
        cookie_btn = page.locator("button.cky-btn-accept").first
        if cookie_btn.is_visible():
            print("  -> Dismissing Cookie Banner...")
            cookie_btn.click()
            time.sleep(1)
    except:
        pass

    # 1. Identify all track icons on the main page
    # The selector provided is: img.trackIcon with alt="Choose icon"
    try:
        # Wait for the first icon to appear
        page.wait_for_selector("img.trackIcon[alt='Choose icon']", timeout=10000)
    except:
        print("warning: No icons found to update.")
        return

    # Use locator to get count and iterate by index to ensure freshness
    icon_locator = page.locator("img.trackIcon[alt='Choose icon']")
    count = icon_locator.count()
    print(f"Found {count} tracks to update.")

    used_icon_srcs = set()

    for i in range(count):
        # 1. Safety Check: Ensure we are still on the edit page
        # The URL for an existing card is .../card/{id}/edit, so we just check for "/edit"
        if "/edit" not in page.url:
            print(f"    -> Error: Navigated away from editor! Current URL: {page.url}")
            print("    -> Stopping icon randomization.")
            break

        try:
            print(f"  -> Updating icon for track {i+1}...")
            
            # Re-locate the specific icon by index
            icon = icon_locator.nth(i)
            
            # --- SMARTER SCROLL LOGIC ---
            # 1. Scroll element into view (usually puts it at the top)
            icon.scroll_into_view_if_needed()
            # 2. Force scroll UP by 150px to move it out from under any sticky header
            page.evaluate("window.scrollBy(0, -150)")
            # 3. Wait a moment for layout to settle
            time.sleep(0.5)

            # Click WITHOUT force=True first. 
            # This allows Playwright to ensure the element is actually not covered.
            try:
                icon.click(timeout=5000) 
            except Exception:
                # If standard click fails (maybe still obscure?), try forcing or scrolling more?
                print("      -> Standard click failed, trying force click...")
                icon.click(force=True)
            
            # Wait for THE RIGHT dialog to open (one that contains track icons)
            target_dialog_selector = "div[role='dialog']:has(img.trackIcon)"
            page.wait_for_selector(target_dialog_selector, state="visible", timeout=5000)
            
            # Wait for icons in dialog to load
            dialog_icons_selector = f"{target_dialog_selector} img.trackIcon"
            page.wait_for_selector(dialog_icons_selector, timeout=5000)
            
            # Get all available icons in the dialog
            available_icons = page.query_selector_all(dialog_icons_selector)
            
            if available_icons:
                # Filter out already used icons based on src
                valid_options = []
                for ico in available_icons:
                    src = ico.get_attribute("src")
                    if src and src not in used_icon_srcs:
                        valid_options.append((ico, src))
                
                # If we ran out of unique icons, reset or just pick from all
                if not valid_options:
                    used_icon_srcs.clear()
                    valid_options = [(ico, ico.get_attribute("src")) for ico in available_icons]

                # Pick one random icon
                choice = random.choice(valid_options)
                chosen_icon_element = choice[0]
                chosen_src = choice[1]
                
                # Mark as used
                if chosen_src:
                    used_icon_srcs.add(chosen_src)

                # Click chosen icon (force to be safe)
                chosen_icon_element.click(force=True)
                
                # Wait for dialog to close
                page.wait_for_selector(target_dialog_selector, state="hidden", timeout=5000)
            else:
                print("    -> No icons found in dialog, pressing Escape.")
                page.keyboard.press("Escape")

            # Increased pause to prevent race conditions or navigation triggers
            print("    -> Waiting 3s for stability...")
            time.sleep(3.0)
            
        except Exception as e:
            print(f"    -> Failed to update icon {i+1}: {e}")
            
            # CRITICAL FIX: Only press Escape if the dialog is actually visible.
            # Pressing Escape on the main page often triggers "Back" or "Exit", causing the script to lose context.
            try:
                # Re-define selector just to be sure we check the right thing
                diag_selector = "div[role='dialog']:has(img.trackIcon)"
                if page.is_visible(diag_selector):
                    print("    -> Dialog appeared stuck open. Closing with Escape.")
                    page.keyboard.press("Escape")
                    # Give it time to close
                    page.wait_for_selector(diag_selector, state="hidden", timeout=3000)
                else:
                    print("    -> Dialog not visible. Skipping Escape to avoid accidental navigation.")
            except Exception as e2:
                print(f"    -> Error attempting to recover: {e2}")


import sys

def run_upload_mode(page: Page, email: str, password: str):
    """Mode 1: Upload tracks and Create playlist."""
    print("\n=== UPLOAD MODE ===")
    
    # Inputs
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

    chunk_size = 3
    chunks = list(chunk_list(audio_files, chunk_size))
    total_chunks = len(chunks)
    
    # 1. Login
    print("Logging in...")
    page.goto("https://us.yotoplay.com/my-account")
    page.fill("input[name='username']", email)
    page.fill("input[name='password']", password)
    page.click("button[type='submit']")
    
    print("Waiting for login...")
    try:
        page.wait_for_url("**/my-account", timeout=60000)
    except Exception:
        print("\n⚠️  Login seems to be taking a while or CAPTCHA appeared.")
        input("    Press Enter in this terminal once you have logged in successfully...")

    # 2. Navigate
    print("Navigating to Playlist Editor...")
    page.goto("https://my.yotoplay.com/card/edit")
    
    # 3. Setup
    print(f"Setting playlist name: {playlist_name}")
    page.fill("input[placeholder='Playlist name']", playlist_name)
    
    # 4. Upload
    for i, chunk in enumerate(chunks, 1):
        upload_chunk(page, chunk, i, total_chunks)
    
    # 5. Wait for processing
    wait_for_processing(page)
    
    # 6. Manual Save
    print("\n--- UPLOAD COMPLETED ---")
    print("Files have been uploaded. Please:")
    print("1. Verify there are no loading spinners.")
    print("2. Click 'Create' manually to save the playlist.")
    print("3. Once saved, copy the URL of the edit page (something like .../card/XXXX/edit) to use in step 2.")
    
    print("\nPress Enter to finish and close the browser...")
    input()


def run_icon_mode(page: Page, email: str, password: str, edit_url: str):
    """Mode 2: Assign random icons to an existing playlist URL."""
    print(f"\n=== ICON MODE ===")
    print(f"Target URL: {edit_url}")
    
    # 1. Login
    print("Logging in...")
    page.goto("https://us.yotoplay.com/my-account")
    page.fill("input[name='username']", email)
    page.fill("input[name='password']", password)
    page.click("button[type='submit']")
    
    print("Waiting for login...")
    try:
        page.wait_for_url("**/my-account", timeout=60000)
    except Exception:
        print("\n⚠️  Login seems to be taking a while or CAPTCHA appeared.")
        input("    Press Enter in this terminal once you have logged in successfully...")

    # 2. Navigate to specific card URL
    print(f"Navigating to: {edit_url}")
    page.goto(edit_url)
    
    # 3. Randomize
    wait_for_processing(page) # Ensure page is ready
    randomize_icons(page)
    
    # 4. Finish
    print("\n--- ASSIGNMENT COMPLETED ---")
    print("Verify icons and click 'Update/Save' if necessary.")
    print("\nPress Enter to close...")
    input()


def main():
    try:
        email, password = get_credentials()
        
        # Check args for mode
        # Usage: python yoto_uploader.py [url]
        target_url = None
        if len(sys.argv) > 1:
            target_url = sys.argv[1]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            # Increase viewport to prevent elements from being hidden under sticky headers
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            
            if target_url:
                run_icon_mode(page, email, password, target_url)
            else:
                run_upload_mode(page, email, password)
            
            browser.close()

    except Exception as e:
        print(f"\nError occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
