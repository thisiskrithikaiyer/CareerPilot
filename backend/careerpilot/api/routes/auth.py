from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt

from careerpilot.config import JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def create_access_token(sub: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": sub, "email": email, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """Validate JWT and return decoded payload. Returns empty dict if auth is disabled."""
    if credentials is None:
        return {}
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """Authenticate via Supabase and return a local JWT."""
    try:
        from gotrue.errors import AuthApiError
        from careerpilot.db.supabase import get_client, get_auth_client

        auth_client = get_auth_client()
        sb_admin = get_client()

        try:
            resp = auth_client.auth.sign_in_with_password({"email": body.email, "password": body.password})
        except AuthApiError as e:
            if "not confirmed" in str(e).lower():
                # Find user and force-confirm via admin API, then retry
                users = sb_admin.auth.admin.list_users()
                match = next((u for u in users if u.email == body.email), None)
                if match:
                    sb_admin.auth.admin.update_user_by_id(str(match.id), {"email_confirm": True})
                    resp = auth_client.auth.sign_in_with_password({"email": body.email, "password": body.password})
                else:
                    raise
            else:
                raise

        user = resp.user
        token = create_access_token(sub=user.id, email=user.email)
        return TokenResponse(access_token=token)
    except Exception as e:
        import traceback
        print(f"\n[AUTH LOGIN ERROR] {type(e).__name__}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/register", response_model=TokenResponse)
async def register(body: LoginRequest):
    try:
        from careerpilot.config import SUPABASE_SERVICE_KEY
        from careerpilot.db.supabase import get_client, get_auth_client

        # Debug: print which key type is loaded (masked)
        key = SUPABASE_SERVICE_KEY
        print(f"[AUTH] SUPABASE_SERVICE_KEY starts with: {key[:20] if key else 'NOT SET'}")
        print(f"[AUTH] Key type hint: {'service_role' if 'service_role' in key else 'anon' if 'anon' in key else 'unknown'}")

        try:
            # Attempt admin create (requires real service role key)
            resp = get_client().auth.admin.create_user({
                "email": body.email,
                "password": body.password,
                "email_confirm": True,
            })
        except Exception as admin_err:
            print(f"[AUTH] Admin create_user failed: {admin_err}")
            print("[AUTH] Falling back to sign_up — disable email confirmation in Supabase dashboard")
            resp = get_auth_client().auth.sign_up({
                "email": body.email,
                "password": body.password,
            })

        user = resp.user
        token = create_access_token(sub=user.id, email=user.email)
        return TokenResponse(access_token=token)
    except Exception as e:
        import traceback
        print(f"\n[AUTH REGISTER ERROR] {type(e).__name__}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
