from functools import lru_cache
from supabase import create_client, Client
from careerpilot.config import SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_ANON_KEY


@lru_cache(maxsize=1)
def get_client() -> Client:
    """Service role client — used for DB reads/writes (bypasses RLS)."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


@lru_cache(maxsize=1)
def get_auth_client() -> Client:
    """Anon key client — used for sign_in / sign_up (required by Supabase Auth)."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
