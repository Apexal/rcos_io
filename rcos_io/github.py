from rcos_io.settings import (
    GITHUB_APP_CLIENT_ID,
    GITHUB_APP_REDIRECT_URL
)

GITHUB_AUTH_URL = f"https://github.com/login/oauth/authorize?client_id={GITHUB_APP_CLIENT_ID}&redirect_uri={GITHUB_APP_REDIRECT_URL}"