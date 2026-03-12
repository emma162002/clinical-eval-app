from passlib.context import CryptContext

# Use pbkdf2_sha256 to avoid bcrypt's 72-byte limit and backend init issues in some environments
pwd_ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)
