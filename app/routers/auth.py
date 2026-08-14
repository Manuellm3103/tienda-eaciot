from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.services.auth_service import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token,
)
from app.services.email_service import email_service
from app.services.email_queue_service import email_queue_service
from app.services.oauth_service import oauth_service
from app.middleware import validate_csrf
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
from app.templates_instance import templates


def _cookie_secure() -> bool:
    """Secure cookies only when HTTPS is expected (prod), so local HTTP dev
    can keep a session without a TLS-terminating proxy."""
    return settings.force_https or settings.frontend_url.startswith("https://")


# ==================== PAGES ====================

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("auth/forgot-password.html", {"request": request})


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str = ""):
    return templates.TemplateResponse("auth/reset-password.html", {"request": request, "token": token})


@router.get("/verify-email", response_class=HTMLResponse)
async def verify_email_page(request: Request, token: str = ""):
    return templates.TemplateResponse("auth/verify-email.html", {"request": request, "token": token})


# ==================== REGISTRO ====================

@router.post("/register", response_model=UserResponse)
async def register(request: Request, data: UserCreate, db: AsyncSession = Depends(get_db)):
    await validate_csrf(request)
    # Check if user exists
    result = await db.execute(select(User).where(User.email == data.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Generate verification token
    verification_token = email_service.generate_verification_token()
    
    # Create user
    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        name=data.name,
        verification_token=verification_token,
        verification_token_expires=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(user)
    await db.flush()
    
    # Queue verification email (delivery via cron worker, never blocks register)
    await email_queue_service.enqueue(
        db,
        to_email=user.email,
        subject="Verifica tu email - Tienda Eaciot",
        html_content=email_service.render_verification_email(user.name or "Usuario", verification_token),
        dedupe_key="VERIFY",
    )

    return user


@router.get("/verify-email/confirm")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    """Verify email with token"""
    result = await db.execute(
        select(User).where(
            User.verification_token == token,
            User.verification_token_expires > datetime.utcnow()
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    await db.flush()
    
    return RedirectResponse(url="/auth/login?verified=true")


@router.post("/resend-verification")
async def resend_verification(email: str, db: AsyncSession = Depends(get_db)):
    """Resend verification email"""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    
    # Generate new token
    verification_token = email_service.generate_verification_token()
    user.verification_token = verification_token
    user.verification_token_expires = datetime.utcnow() + timedelta(hours=24)
    await db.flush()
    
    # Queue email (idempotent: reuses any pending verification email)
    await email_queue_service.enqueue(
        db,
        to_email=user.email,
        subject="Verifica tu email - Tienda Eaciot",
        html_content=email_service.render_verification_email(user.name or "Usuario", verification_token),
        dedupe_key="VERIFY",
    )

    return {"message": "Verification email queued"}


# ==================== LOGIN ====================

@router.post("/login", response_model=Token)
async def login(data: UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    # Find user
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    
    if not user or not user.hashed_password or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Create token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # Set cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=30 * 24 * 60 * 60,  # 30 days
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login/web")
async def login_web(request: Request, data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login for web forms - returns redirect with a session cookie."""
    await validate_csrf(request)
    # Find user
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Create token
    access_token = create_access_token(data={"sub": str(user.id)})

    # Redirect with cookie
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=30 * 24 * 60 * 60,
    )

    return response


# ==================== PASSWORD RESET ====================

@router.post("/forgot-password")
async def forgot_password(request: Request, email: str, db: AsyncSession = Depends(get_db)):
    """Send password reset email"""
    await validate_csrf(request)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        # Don't reveal if user exists
        return {"message": "If email exists, reset link was sent"}
    
    # Generate reset token
    reset_token = email_service.generate_verification_token()
    user.reset_token = reset_token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    await db.flush()
    
    # Queue email (delivery via cron worker)
    await email_queue_service.enqueue(
        db,
        to_email=user.email,
        subject="Restablecer contraseña - Tienda Eaciot",
        html_content=email_service.render_password_reset_email(user.name or "Usuario", reset_token),
        dedupe_key="RESET",
    )

    return {"message": "If email exists, reset link was sent"}


@router.post("/reset-password")
async def reset_password(request: Request, token: str, new_password: str, db: AsyncSession = Depends(get_db)):
    """Reset password with token"""
    await validate_csrf(request)
    result = await db.execute(
        select(User).where(
            User.reset_token == token,
            User.reset_token_expires > datetime.utcnow()
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    user.hashed_password = get_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    await db.flush()
    
    return {"message": "Password reset successfully"}


# ==================== GOOGLE OAUTH ====================

@router.get("/google")
async def google_login(request: Request):
    """Redirect to Google OAuth"""
    state = request.query_params.get("next", "/")
    auth_url = await oauth_service.get_google_auth_url(state)
    return RedirectResponse(auth_url)


@router.get("/google/callback")
async def google_callback(code: str, state: str = "/", db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth callback"""
    try:
        # Exchange code for tokens
        token_data = await oauth_service.exchange_google_code(code)
        
        # Get user info
        user_info = await oauth_service.get_google_user_info(token_data["access_token"])
        
        # Find or create user
        result = await db.execute(select(User).where(User.google_id == user_info["sub"]))
        user = result.scalar_one_or_none()
        
        if not user:
            # Check if user exists with same email
            result = await db.execute(select(User).where(User.email == user_info["email"]))
            user = result.scalar_one_or_none()
            
            if user:
                # Link Google account
                user.google_id = user_info["sub"]
            else:
                # Create new user
                user = User(
                    email=user_info["email"],
                    name=user_info.get("name"),
                    picture=user_info.get("picture"),
                    google_id=user_info["sub"],
                    email_verified=user_info.get("email_verified", False),
                )
                db.add(user)
        
        await db.commit()

        # Create token and redirect
        access_token = create_access_token(data={"sub": str(user.id)})
        response = RedirectResponse(url=state)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=_cookie_secure(),
            samesite="none",
            max_age=30 * 24 * 60 * 60,
        )

        return response

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ==================== MICROSOFT OAUTH ====================

@router.get("/microsoft")
async def microsoft_login(request: Request):
    """Redirect to Microsoft OAuth"""
    state = request.query_params.get("next", "/")
    auth_url = await oauth_service.get_microsoft_auth_url(state)
    return RedirectResponse(auth_url)


@router.get("/microsoft/callback")
async def microsoft_callback(code: str, state: str = "/", db: AsyncSession = Depends(get_db)):
    """Handle Microsoft OAuth callback"""
    try:
        # Exchange code for tokens
        token_data = await oauth_service.exchange_microsoft_code(code)
        
        # Get user info
        user_info = await oauth_service.get_microsoft_user_info(token_data["access_token"])
        
        # Find or create user
        result = await db.execute(select(User).where(User.microsoft_id == user_info["id"]))
        user = result.scalar_one_or_none()
        
        if not user:
            # Check if user exists with same email
            email = user_info.get("mail") or user_info.get("userPrincipalName")
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            
            if user:
                # Link Microsoft account
                user.microsoft_id = user_info["id"]
            else:
                # Create new user
                user = User(
                    email=email,
                    name=user_info.get("displayName"),
                    microsoft_id=user_info["id"],
                    email_verified=True,  # Microsoft emails are verified
                )
                db.add(user)
        
        await db.commit()

        # Create token and redirect
        access_token = create_access_token(data={"sub": str(user.id)})
        response = RedirectResponse(url=state)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=_cookie_secure(),
            samesite="none",
            max_age=30 * 24 * 60 * 60,
        )

        return response

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ==================== GITHUB OAUTH ====================

@router.get("/github")
async def github_login(request: Request):
    """Redirect to GitHub OAuth"""
    state = request.query_params.get("next", "/")
    auth_url = await oauth_service.get_github_auth_url(state)
    return RedirectResponse(auth_url)


@router.get("/github/callback")
async def github_callback(code: str, state: str = "/", db: AsyncSession = Depends(get_db)):
    """Handle GitHub OAuth callback"""
    try:
        # Exchange code for tokens
        token_data = await oauth_service.exchange_github_code(code)
        
        # Get user info
        user_info = await oauth_service.get_github_user_info(token_data["access_token"])
        
        # Get email (may be private)
        email = user_info.get("email")
        if not email:
            email = await oauth_service.get_github_user_email(token_data["access_token"])
        
        # Find or create user
        result = await db.execute(select(User).where(User.github_id == str(user_info["id"])))
        user = result.scalar_one_or_none()
        
        if not user:
            # Check if user exists with same email
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            
            if user:
                # Link GitHub account
                user.github_id = str(user_info["id"])
            else:
                # Create new user
                user = User(
                    email=email,
                    name=user_info.get("name") or user_info.get("login"),
                    picture=user_info.get("avatar_url"),
                    github_id=str(user_info["id"]),
                    email_verified=True,  # GitHub emails are verified
                )
                db.add(user)
        
        await db.commit()

        # Create token and redirect
        access_token = create_access_token(data={"sub": str(user.id)})
        response = RedirectResponse(url=state)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=_cookie_secure(),
            samesite="none",
            max_age=30 * 24 * 60 * 60,
        )

        return response

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ==================== UTILITIES ====================

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token")
    return response


@router.get("/me", response_model=UserResponse)
async def me(request: Request, db: AsyncSession = Depends(get_db)):
    # Get token from cookie
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Verify token
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.get("/check")
async def check_auth(request: Request):
    """Check if user is authenticated"""
    token = request.cookies.get("access_token")
    if not token:
        return {"authenticated": False}
    
    payload = verify_token(token)
    if not payload:
        return {"authenticated": False}
    
    return {"authenticated": True, "user_id": payload.get("sub")}
