from auth0.authentication import GetToken
from auth0.authentication import Users
from auth0.management import Auth0 as Auth0Management
from app.config import settings
import httpx


class Auth0Service:
    def __init__(self):
        self.domain = settings.auth0_domain
        self.client_id = settings.auth0_client_id
        self.client_secret = settings.auth0_client_secret
        self.callback_url = settings.auth0_callback_url
        self.audience = settings.auth0_audience
    
    def get_login_url(self, state: str = "/") -> str:
        return (
            f"https://{self.domain}/authorize?"
            f"response_type=code&"
            f"client_id={self.client_id}&"
            f"redirect_uri={self.callback_url}&"
            f"scope=openid profile email&"
            f"audience={self.audience}&"
            f"state={state}"
        )
    
    async def exchange_code(self, code: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://{self.domain}/oauth/token",
                json={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.callback_url,
                },
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_info(self, access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://{self.domain}/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()
    
    def get_logout_url(self, return_to: str = "/") -> str:
        return (
            f"https://{self.domain}/v2/logout?"
            f"client_id={self.client_id}&"
            f"returnTo={return_to}"
        )


auth0_service = Auth0Service()
