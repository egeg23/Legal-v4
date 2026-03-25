"""
Authentication module for Legal AI Service.
Handles user registration, login, and JWT token management.
"""

import jwt
import re
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from models import db, User
from werkzeug.security import generate_password_hash

import os

# Configuration
JWT_SECRET = os.environ.get('JWT_SECRET_KEY')
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET_KEY environment variable must be set")
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24
REFRESH_TOKEN_EXPIRATION_DAYS = 30


def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_username(username):
    """Validate username format."""
    if not username or len(username) < 3 or len(username) > 50:
        return False
    # Allow letters, numbers, underscores, hyphens
    pattern = r'^[a-zA-Z0-9_-]+$'
    return re.match(pattern, username) is not None


def validate_password(password):
    """Validate password strength."""
    if not password or len(password) < 6:
        return False
    return True


def generate_token(user_id, token_type='access'):
    """Generate JWT token for user."""
    if token_type == 'access':
        expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    else:  # refresh token
        expiration = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRATION_DAYS)
    
    payload = {
        'user_id': user_id,
        'type': token_type,
        'exp': expiration,
        'iat': datetime.utcnow()
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token):
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_client_ip():
    """Get client IP address from request."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr


def get_auth_token():
    """Extract token from Authorization header."""
    auth_header = request.headers.get('Authorization')
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == 'bearer':
            return parts[1]
    return None


def require_auth(f):
    """Decorator to require authentication for endpoint."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_auth_token()
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'message': 'Please provide a valid authentication token'
            }), 401
        
        payload = decode_token(token)
        if not payload or payload.get('type') != 'access':
            return jsonify({
                'success': False,
                'error': 'Invalid token',
                'message': 'Token is invalid or expired'
            }), 401
        
        user = User.query.get(payload['user_id'])
        if not user or not user.is_active:
            return jsonify({
                'success': False,
                'error': 'User not found',
                'message': 'User account not found or deactivated'
            }), 401
        
        # Attach user to request
        request.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function


def get_current_user():
    """Get current authenticated user."""
    return getattr(request, 'current_user', None)


def register_user(username, email, password, ip_address=None):
    """
    Register a new user.
    
    Args:
        username: User login name
        email: User email
        password: User password
        ip_address: Client IP address
    
    Returns:
        Tuple of (user, error_message)
    """
    # Validate username
    if not validate_username(username):
        return None, 'Имя пользователя должно содержать от 3 до 50 символов и может включать только буквы, цифры, дефисы и подчеркивания'
    
    # Validate email
    if not email or not validate_email(email):
        return None, 'Пожалуйста, введите корректный email адрес'
    
    # Validate password
    if not validate_password(password):
        return None, 'Пароль должен содержать минимум 6 символов'
    
    # Check if username exists
    if User.query.filter_by(username=username.lower()).first():
        return None, 'Пользователь с таким именем уже существует'
    
    # Check if email exists
    if User.query.filter_by(email=email.lower()).first():
        return None, 'Пользователь с таким email уже существует'
    
    # Create new user
    user = User(
        username=username,
        email=email,
        password=password,
        ip_address=ip_address
    )
    
    try:
        db.session.add(user)
        db.session.commit()
        return user, None
    except Exception as e:
        db.session.rollback()
        return None, f'Ошибка при регистрации: {str(e)}'


def login_user(username_or_email, password, ip_address=None):
    """
    Authenticate user and return user object.
    
    Args:
        username_or_email: Username or email
        password: User password
        ip_address: Client IP address
    
    Returns:
        Tuple of (user, error_message)
    """
    if not username_or_email or not password:
        return None, 'Укажите имя пользователя/email и пароль'
    
    # Try to find user by username or email
    user = User.query.filter(
        db.or_(
            User.username == username_or_email.lower(),
            User.email == username_or_email.lower()
        )
    ).first()
    
    if not user:
        return None, 'Неверное имя пользователя/email или пароль'
    
    if not user.check_password(password):
        return None, 'Неверное имя пользователя/email или пароль'
    
    if not user.is_active:
        return None, 'Учетная запись деактивирована'
    
    # Update last login
    user.last_login = datetime.utcnow()
    if ip_address:
        user.ip_address = ip_address
    db.session.commit()
    
    return user, None


def refresh_access_token(refresh_token):
    """
    Generate new access token from refresh token.
    
    Args:
        refresh_token: Refresh token string
    
    Returns:
        Tuple of (new_access_token, error_message)
    """
    payload = decode_token(refresh_token)
    
    if not payload or payload.get('type') != 'refresh':
        return None, 'Invalid refresh token'
    
    user = User.query.get(payload['user_id'])
    if not user or not user.is_active:
        return None, 'User not found or deactivated'
    
    new_token = generate_token(user.id, 'access')
    return new_token, None


def auth_response(user, message='Success'):
    """Generate authentication response with tokens."""
    access_token = generate_token(user.id, 'access')
    refresh_token = generate_token(user.id, 'refresh')
    
    return jsonify({
        'success': True,
        'message': message,
        'data': {
            'user': user.to_dict(),
            'tokens': {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_in': JWT_EXPIRATION_HOURS * 3600
            }
        }
    })


def error_response(message, error_code='ERROR', status_code=400):
    """Generate error response."""
    return jsonify({
        'success': False,
        'error': error_code,
        'message': message
    }), status_code
