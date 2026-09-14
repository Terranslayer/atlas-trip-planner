from werkzeug.security import generate_password_hash, check_password_hash

from .sqlite import get_conn


def create(username: str, password: str) -> int:
    # Pin pbkdf2:sha256 explicitly: Werkzeug >= 3 switched the default to scrypt,
    # which is unavailable on stock Python builds without OpenSSL scrypt support.
    pw_hash = generate_password_hash(password, method="pbkdf2:sha256")
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, pw_hash),
    )
    conn.commit()
    return cur.lastrowid


def find_by_id(user_id: int):
    return get_conn().execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()


def find_by_username(username: str):
    return get_conn().execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()


def authenticate(username: str, password: str):
    user = find_by_username(username)
    if user is None:
        return None
    if not check_password_hash(user["password_hash"], password):
        return None
    return user
