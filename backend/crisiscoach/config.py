import os
from dotenv import load_dotenv

load_dotenv()

# LLM
GROQ_API_KEY: str = os.environ.get("GROK_API_KEY", "")
GROQ_API_KEY_2: str = os.environ.get("GROQ_API_KEY_2", "")
GROQ_MODEL: str = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

# Supabase
SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY: str = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_ANON_KEY: str = os.environ.get("SUPABASE_ANON_KEY", "")

# Redis
REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379")

# Vector store
CHROMA_PERSIST_DIR: str = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db")

# Auth
JWT_SECRET: str = os.environ.get("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# LangSmith (optional)
LANGCHAIN_API_KEY: str = os.environ.get("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT: str = os.environ.get("LANGCHAIN_PROJECT", "crisiscoach")

# App
CORS_ORIGINS: list[str] = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
