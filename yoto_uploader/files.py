from pathlib import Path
from typing import Iterable, List


VALID_EXTENSIONS = {".mp3", ".m4a", ".wav", ".m4b"}


def get_valid_audio_files(folder_path: str) -> List[Path]:
    """Return sorted list of valid audio files in the given folder.

    Args:
        folder_path: Path to the folder to scan.

    Raises:
        FileNotFoundError: If the folder does not exist.

    Returns:
        List of Path objects sorted alphabetically.
    """
    path = Path(folder_path)
    if not path.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    files = [
        f
        for f in path.iterdir()
        if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS
    ]
    files.sort(key=lambda x: x.name)
    return files


def chunk_list(data: Iterable, size: int):
    """Yield successive n-sized chunks from data."""
    data_list = list(data)
    for i in range(0, len(data_list), size):
        yield data_list[i : i + size]
