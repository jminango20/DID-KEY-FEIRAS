import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    SECRET_KEY: str = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    ENV: str = os.getenv('FLASK_ENV', 'development')
    DEBUG: bool = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    # Admin credentials
    ADMIN_USERNAME: str = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD: str = os.getenv('ADMIN_PASSWORD', 'admin123')

    # Supabase
    SUPABASE_URL: str = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY: str = os.getenv('SUPABASE_KEY', '')

    # Association DID:KEY — base64 of raw 32-byte Ed25519 private key
    ASSOCIATION_PRIVATE_KEY_B64: str = os.getenv('ASSOCIATION_PRIVATE_KEY_B64', '')

    # Set at runtime by app.py after key bootstrap
    ASSOCIATION_DID: str = ''
    ASSOCIATION_PRIVATE_KEY_BYTES: bytes = b''


config = Config()
