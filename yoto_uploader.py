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
    print(f"Subiendo lote {chunk_index} de {total_chunks}...")
    
    file_paths = [str(f.absolute()) for f in chunk_files]
    
    # robust approach: target the hidden input directly
    # This avoids the instability of clicking the label and waiting for the file chooser
    try:
        page.set_input_files("#upload", file_paths)
    except Exception as e:
        print(f"  -> Error subiendo archivos directamente: {e}")
        print("  -> Intentando método alternativo (Click)...")
        with page.expect_file_chooser() as fc_info:
            page.click("label:has-text('Add audio')")
        file_chooser = fc_info.value
        file_chooser.set_files(file_paths)

    # --- LOGIC CORE: Wait for upload completion ---
    print(f"  -> Esperando procesamiento del lote {chunk_index}...")
    
    # Validation relaxation: File names often change/shorten on the platform.
    # Instead of strict name checking, we rely on a generous wait and visual progress.
    # We wait a bit longer to be safe since we removed the strict check.
    time.sleep(10) 
    
    print(f"  -> Lote {chunk_index} completado (Tiempo de espera finalizado).")

def randomize_icons(page: Page):
    """Assigns a random icon to each uploaded track."""
    print("\n--- Asignando iconos aleatorios ---")
    import random
    
    # 1. Identify all track icons on the main page
    # The selector provided is: img.trackIcon with alt="Choose icon"
    try:
        # Wait for the first icon to appear
        page.wait_for_selector("img.trackIcon[alt='Choose icon']", timeout=10000)
    except:
        print("warning: No icons found to update.")
        return

    # Select all icons that are for choosing a new icon
    icons = page.query_selector_all("img.trackIcon[alt='Choose icon']")
    print(f"Found {len(icons)} tracks to update.")

    for i, icon in enumerate(icons, 1):
        try:
            print(f"  -> Updating icon for track {i}...")
            # Click the icon to open dialog
            icon.click()
            
            # Wait for dialog to open
            # Selector for dialog: div[role="dialog"]
            page.wait_for_selector("div[role='dialog']", state="visible", timeout=5000)
            
            # Wait for icons in dialog to load
            # Selector from user: div[role="dialog"] img.trackIcon
            dialog_icons_selector = "div[role='dialog'] img.trackIcon"
            page.wait_for_selector(dialog_icons_selector, timeout=5000)
            
            # Get all available icons in the dialog
            available_icons = page.query_selector_all(dialog_icons_selector)
            
            if available_icons:
                # Pick one random icon
                chosen_icon = random.choice(available_icons)
                chosen_icon.click()
                
                # Wait for dialog to close
                page.wait_for_selector("div[role='dialog']", state="hidden", timeout=5000)
            else:
                print("    -> No icons found in dialog, pressing Escape.")
                page.keyboard.press("Escape")

            # Small pause to be gentle
            time.sleep(0.5)
            
        except Exception as e:
            print(f"    -> Failed to update icon {i}: {e}")
            # Ensure we close dialog if stuck open
            page.keyboard.press("Escape")


def main():
    try:
        # Get playlist name from user
        playlist_name = input("Enter playlist name: ").strip()
        while not playlist_name:
            print("Playlist name cannot be empty.")
            playlist_name = input("Enter playlist name: ").strip()

        email, password = get_credentials()
        folder_input = input("Enter path to audio folder: ").strip()
        # Remove quotes if user dragged/dropped folder
        folder_input = folder_input.replace("'", "").replace('"', "")
        
        audio_files = get_valid_audio_files(folder_input)
        
        if not audio_files:
            print("No valid audio files found (.mp3, .m4a, .wav, .m4b).")
            return

        chunk_size = 3
        chunks = list(chunk_list(audio_files, chunk_size))
        total_chunks = len(chunks)
        
        print(f"Found {len(audio_files)} files. Split into {total_chunks} chunk(s).")
        
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            
            # 1. Login
            print("Logging in...")
            page.goto("https://us.yotoplay.com/my-account")
            # Selectors updated based on provided HTML
            page.fill("input[name='username']", email)
            page.fill("input[name='password']", password)
            page.click("button[type='submit']")
            
            # Wait for login to complete
            page.wait_for_url("**/my-account", timeout=30000)
            
            # 2. Navigate directly to My Cards / Edit
            print("Navigating to Playlist Editor...")
            # User confirmed we can go directly here after login
            page.goto("https://my.yotoplay.com/card/edit")
            
            # 2.5 Fill Playlist Name
            print(f"Setting playlist name: {playlist_name}")
            page.fill("input[placeholder='Playlist name']", playlist_name)
            
            # 3. Batch Upload
            for i, chunk in enumerate(chunks, 1):
                upload_chunk(page, chunk, i, total_chunks)
            
            # 3.5 Randomize Icons
            randomize_icons(page)

            # 4. Save/Create
            print("All chunks uploaded. Saving playlist...")
            page.click("button.create-btn")
            
            print("Waiting for save to complete...")
            page.wait_for_timeout(5000)
            
            print("\nCarga completa y guardada! Presiona Enter en la terminal para cerrar...")
            input()
            browser.close()

    except Exception as e:
        print(f"\nError occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
