import os


def get_github_token() -> str:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Set GITHUB_TOKEN in backend/.env")
    return token


if __name__ == "__main__":
    get_github_token()
    print("GITHUB_TOKEN is configured.")
