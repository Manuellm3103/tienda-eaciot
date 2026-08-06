import httpx
from app.config import settings
from typing import Optional


class OAuthService:
    """Service for handling OAuth authentication with multiple providers"""
    
    # Google OAuth
    async def get_google_auth_url(self, state: str = "/") -> str:
        """Get Google OAuth authorization URL"""
        return (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={settings.google_client_id}&"
            f"redirect_uri={settings.google_redirect_uri}&"
            "response_type=code&"
            "scope=openid email profile&"
            f"state={state}"
        )
    
    async def exchange_google_code(self, code: str) -> dict:
        """Exchange Google OAuth code for tokens"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            return response.json()
    
    async def get_google_user_info(self, access_token: str) -> dict:
        """Get user info from Google"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()
    
    # Microsoft OAuth
    async def get_microsoft_auth_url(self, state: str = "/") -> str:
        """Get Microsoft OAuth authorization URL"""
        return (
            "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
            f"client_id={settings.microsoft_client_id}&"
            f"redirect_uri={settings.microsoft_redirect_uri}&"
            "response_type=code&"
            "scope=openid email profile User.Read&"
            f"state={state}"
        )
    
    async def exchange_microsoft_code(self, code: str) -> dict:
        """Exchange Microsoft OAuth code for tokens"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                data={
                    "code": code,
                    "client_id": settings.microsoft_client_id,
                    "client_secret": settings.microsoft_client_secret,
                    "redirect_uri": settings.microsoft_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            return response.json()
    
    async def get_microsoft_user_info(self, access_token: str) -> dict:
        """Get user info from Microsoft"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()
    
    # GitHub OAuth
    async def get_github_auth_url(self, state: str = "/") -> str:
        """Get GitHub OAuth authorization URL"""
        return (
            "https://github.com/login/oauth/authorize?"
            f"client_id={settings.github_client_id}&"
            f"redirect_uri={settings.github_redirect_uri}&"
            "scope=user:email&"
            f"state={state}"
        )
    
    async def exchange_github_code(self, code: str) -> dict:
        """Exchange GitHub OAuth code for tokens"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                json={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()
    
    async def get_github_user_info(self, access_token: str) -> dict:
        """Get user info from GitHub"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            return response.json()
    
    async def get_github_user_email(self, access_token: str) -> Optional[str]:
        """Get user email from GitHub (may be private)"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            emails = response.json()
            # Find primary email
            for email in emails:
                if email.get("primary"):
                    return email.get("email")
            return emails[0].get("email") if emails else None


oauth_service = OAuthService()
