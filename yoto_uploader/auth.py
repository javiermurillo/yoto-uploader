import os
from typing import Tuple

from dotenv import load_dotenv

# Load environment variables once at module import time
load_dotenv()


def get_credentials() -> Tuple[str, str]:
    """Retrieve Yoto credentials from env variables or prompt the user.

    Returns:
        Tuple of (email, password).
    """

    email = os.getenv("YOTO_EMAIL")
    password = os.getenv("YOTO_PASSWORD")

    if not email:
        email = input("Enter Yoto Email: ")
    if not password:
        password = input("Enter Yoto Password: ")

    return email, password
