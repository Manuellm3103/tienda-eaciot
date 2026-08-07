"""CORS configuration"""

from fastapi.middleware.cors import CORSMiddleware
from app.config import settings


def setup_cors(app):
    """Configure CORS middleware"""
    
    # Allowed origins
    origins = [
        settings.frontend_url,
        "http://localhost:3000",  # Development
        "http://localhost:8000",  # Development
    ]
    
    # Add production domain
    if settings.frontend_url and settings.frontend_url != "http://localhost:8000":
        origins.append(settings.frontend_url)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-CSRF-Token",
        ],
        expose_headers=["X-Total-Count", "X-Page-Count"],
        max_age=600,  # 10 minutes
    )
