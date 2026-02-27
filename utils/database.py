from typing import Optional
from supabase import create_client, Client

from config import config

_client: Optional[Client] = None


def get_supabase_client() -> Client:
    global _client

    if _client is None:
        if not config.SUPABASE_URL or config.SUPABASE_URL == 'https://your-project.supabase.co':
            raise ValueError(
                "SUPABASE_URL is not configured. "
                "Add your Supabase project URL to .env"
            )
        if not config.SUPABASE_KEY or config.SUPABASE_KEY == 'your-supabase-anon-key':
            raise ValueError(
                "SUPABASE_KEY is not configured. "
                "Add your Supabase anon key to .env"
            )

        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

    return _client
