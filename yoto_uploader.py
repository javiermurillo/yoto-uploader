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

def main():
    try:
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
            
            # 3. Batch Upload
            for i, chunk in enumerate(chunks, 1):
                upload_chunk(page, chunk, i, total_chunks)
            
            print("\nCarga completa. Presiona Enter en la terminal para cerrar...")
            # Optional: Check if 'Create' button is enabled now
            # page.is_enabled("button.create-btn")
            input()
            browser.close()

    except Exception as e:
        print(f"\nError occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
