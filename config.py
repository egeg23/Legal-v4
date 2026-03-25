"""
Configuration for Legal AI Service
"""

import os

# Directories
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}

# API
API_PREFIX = '/api'

# Logging
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = 'legal_ai.log'

# Database
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///legal_ai.db')

# Security
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# KIMI API
KIMI_API_KEY = os.environ.get('KIMI_API_KEY', '')
KIMI_API_URL = os.environ.get('KIMI_API_URL', 'https://api.moonshot.cn/v1')


def init_config(app):
    """Initialize Flask app with configuration."""
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    
    # Create upload folder if it doesn't exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def init_tariffs():
    """Initialize default tariffs in database."""
    from models import db, Tariff
    
    # Define default tariffs
    tariffs = [
        {
            'code': 'single',
            'name': 'Разовый',
            'price': 5000,
            'credits': 1,
            'max_documents': 3,
            'clarity_requests': 0,
            'has_strategy': False,
            'has_defense_speech': False,
            'has_case_audit': False,
            'has_explanation_bonus': True,
            'description': 'Для людей, далёких от юриспруденции. Включает бонусное разъяснение простым языком.'
        },
        {
            'code': 'advocate',
            'name': 'Адвокат',
            'price': 175000,
            'credits': 50,
            'max_documents': 7,
            'clarity_requests': 50,
            'has_strategy': False,
            'has_defense_speech': False,
            'has_case_audit': False,
            'has_explanation_bonus': False,
            'description': 'Для адвокатов. Возможность внести ясность по каждому документу. AI учится на правках.'
        },
        {
            'code': 'firm',
            'name': 'Фирма',
            'price': 500000,
            'credits': 175,
            'max_documents': 10,
            'clarity_requests': 175,
            'has_strategy': False,
            'has_defense_speech': False,
            'has_case_audit': False,
            'has_explanation_bonus': False,
            'description': 'Для юридических фирм. Экономия 18% vs тариф Адвокат. AI учится на правках.'
        },
        {
            'code': 'chamber',
            'name': 'Палата',
            'price': 1500000,
            'credits': 500,
            'max_documents': 20,
            'clarity_requests': 10,
            'has_strategy': True,
            'has_defense_speech': True,
            'has_case_audit': True,
            'has_explanation_bonus': False,
            'description': 'Для адвокатских палат. Эксклюзивные фичи: стратегия защиты, речь защиты, аудит судебной практики.'
        }
    ]
    
    created_count = 0
    for tariff_data in tariffs:
        existing = Tariff.query.filter_by(code=tariff_data['code']).first()
        if not existing:
            tariff = Tariff(**tariff_data)
            db.session.add(tariff)
            created_count += 1
    
    if created_count > 0:
        db.session.commit()
        print(f"[INIT] Created {created_count} default tariffs")
    else:
        print("[INIT] All tariffs already exist")
    
    return created_count
