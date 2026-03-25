"""
Database models for Legal AI Service.
Contains SQLAlchemy models for users, cases, and download history.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import json
import uuid

db = SQLAlchemy()


class User(db.Model):
    """User model for storing user information."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    
    # Credit system fields
    credits = db.Column(db.Integer, default=0)  # кредитный баланс
    is_first_purchase = db.Column(db.Boolean, default=True)
    discount_used = db.Column(db.Boolean, default=False)
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_code = db.Column(db.String(10), nullable=True)
    email_verification_expires = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    cases = db.relationship('Case', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    downloads = db.relationship('DownloadHistory', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    ip_requests = db.relationship('IPRequest', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    user_tariffs = db.relationship('UserTariff', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    clarity_requests = db.relationship('ClarityRequest', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, username, email, password, ip_address=None):
        self.username = username.lower().strip()
        self.email = email.lower().strip()
        self.password_hash = generate_password_hash(password)
        self.ip_address = ip_address
    
    def check_password(self, password):
        """Verify password against stored hash."""
        return check_password_hash(self.password_hash, password)
    
    def set_password(self, password):
        """Set new password."""
        self.password_hash = generate_password_hash(password)
    
    def to_dict(self, include_sensitive=False):
        """Convert user to dictionary."""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'cases_count': self.cases.count()
        }
        if include_sensitive:
            data['ip_address'] = self.ip_address
        return data
    
    def __repr__(self):
        return f'<User {self.username}>'


class Case(db.Model):
    """Case model for storing legal cases and their analysis."""
    
    __tablename__ = 'cases'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    case_title = db.Column(db.String(255), nullable=False)
    document_type = db.Column(db.String(50), nullable=True)  # 'complaint', 'appeal', 'petition', 'statement'
    custom_request = db.Column(db.Text, nullable=True)  # Custom text request
    documents_json = db.Column(db.Text, nullable=True)  # JSON string of document paths
    analysis_result = db.Column(db.Text, nullable=True)  # JSON string of analysis results
    status = db.Column(db.String(50), default='pending', nullable=False)  # pending, analyzing, completed, failed, paid
    progress = db.Column(db.Integer, default=0, nullable=False)  # 0-100 progress percentage
    progress_message = db.Column(db.String(255), nullable=True)  # Current progress message
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    paid = db.Column(db.Boolean, default=False, nullable=False)
    paid_at = db.Column(db.DateTime, nullable=True)
    price = db.Column(db.Integer, default=5000, nullable=False)  # Price in rubles
    analysis_started_at = db.Column(db.DateTime, nullable=True)
    analysis_completed_at = db.Column(db.DateTime, nullable=True)
    case_token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    generated_document_path = db.Column(db.String(500), nullable=True)  # Path to generated DOCX
    
    # Relationships
    downloads = db.relationship('DownloadHistory', backref='case', lazy='dynamic', cascade='all, delete-orphan')
    payment = db.relationship('PaymentTransaction', backref='case', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, user_id, case_title, document_type=None, custom_request=None, documents=None):
        self.user_id = user_id
        self.case_title = case_title
        self.document_type = document_type
        self.custom_request = custom_request
        self.documents_json = json.dumps(documents or [])
        self.price = 5000  # Fixed price
    
    def get_documents(self):
        """Get list of document paths."""
        if self.documents_json:
            return json.loads(self.documents_json)
        return []
    
    def set_documents(self, documents):
        """Set list of document paths."""
        self.documents_json = json.dumps(documents)
    
    def add_document(self, document_path):
        """Add a document to the case."""
        documents = self.get_documents()
        documents.append(document_path)
        self.set_documents(documents)
    
    def get_analysis_result(self):
        """Get analysis result as dictionary."""
        if self.analysis_result:
            return json.loads(self.analysis_result)
        return None
    
    def set_analysis_result(self, result):
        """Set analysis result."""
        self.analysis_result = json.dumps(result)
    
    def mark_as_paid(self):
        """Mark case as paid."""
        self.paid = True
        self.paid_at = datetime.utcnow()
        self.status = 'paid'
    
    def start_analysis(self):
        """Mark analysis as started."""
        self.status = 'analyzing'
        self.analysis_started_at = datetime.utcnow()
        self.progress = 0
    
    def update_progress(self, progress, message):
        """Update progress percentage and message."""
        self.progress = min(100, max(0, progress))
        self.progress_message = message
    
    def complete_analysis(self, result=None):
        """Mark analysis as completed."""
        self.status = 'completed'
        self.progress = 100
        self.analysis_completed_at = datetime.utcnow()
        if result:
            self.set_analysis_result(result)
    
    def fail_analysis(self):
        """Mark analysis as failed."""
        self.status = 'failed'
    
    def get_status_display(self):
        """Get human-readable status."""
        status_map = {
            'pending': 'Ожидает обработки',
            'analyzing': 'В обработке',
            'completed': 'Готово',
            'failed': 'Ошибка',
            'paid': 'Оплачено'
        }
        return status_map.get(self.status, self.status)
    
    def to_dict(self, include_analysis=False):
        """Convert case to dictionary."""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'case_title': self.case_title,
            'document_type': self.document_type,
            'document_type_display': self.get_document_type_display(),
            'custom_request': self.custom_request,
            'status': self.status,
            'status_display': self.get_status_display(),
            'progress': self.progress,
            'progress_message': self.progress_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'paid': self.paid,
            'price': self.price,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'documents_count': len(self.get_documents()),
            'case_token': self.case_token,
            'generated_document_path': self.generated_document_path
        }
        if include_analysis:
            data['analysis_result'] = self.get_analysis_result()
            data['documents'] = self.get_documents()
        return data
    
    def get_document_type_display(self):
        """Get human-readable document type."""
        type_map = {
            'complaint': 'Исковое заявление',
            'appeal': 'Апелляционная жалоба',
            'petition': 'Претензия',
            'statement': 'Стратегия защиты'
        }
        if self.document_type:
            return type_map.get(self.document_type, self.document_type)
        return 'Пользовательский запрос' if self.custom_request else 'Не указан'
    
    def __repr__(self):
        return f'<Case {self.case_title}>'


class DownloadHistory(db.Model):
    """Model for tracking document downloads."""
    
    __tablename__ = 'download_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.id'), nullable=False, index=True)
    downloaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    download_type = db.Column(db.String(50), default='documents', nullable=False)
    
    def __init__(self, user_id, case_id, ip_address=None, user_agent=None, download_type='documents'):
        self.user_id = user_id
        self.case_id = case_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.download_type = download_type
    
    def to_dict(self):
        """Convert download history to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'case_id': self.case_id,
            'downloaded_at': self.downloaded_at.isoformat() if self.downloaded_at else None,
            'download_type': self.download_type
        }
    
    def __repr__(self):
        return f'<DownloadHistory user={self.user_id} case={self.case_id}>'


class IPRequest(db.Model):
    """Model for tracking IP-based requests for rate limiting."""
    
    __tablename__ = 'ip_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=False, index=True)
    request_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    request_type = db.Column(db.String(50), nullable=False)
    
    def __init__(self, user_id, ip_address, request_type):
        self.user_id = user_id
        self.ip_address = ip_address
        self.request_type = request_type
    
    @staticmethod
    def get_request_count(user_id, ip_address, days=30):
        """Get number of requests from user/IP in the last N days."""
        since = datetime.utcnow() - timedelta(days=days)
        return IPRequest.query.filter(
            IPRequest.user_id == user_id,
            IPRequest.ip_address == ip_address,
            IPRequest.request_date >= since
        ).count()
    
    @staticmethod
    def can_make_request(user_id, ip_address, max_requests=200, days=30):
        """Check if user can make a request based on rate limits."""
        count = IPRequest.get_request_count(user_id, ip_address, days)
        return count < max_requests
    
    def __repr__(self):
        return f'<IPRequest {self.ip_address} {self.request_type}>'


class PaymentTransaction(db.Model):
    """Model for storing payment transactions."""
    
    __tablename__ = 'payment_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.id'), nullable=True, index=True)
    amount = db.Column(db.Integer, nullable=False)  # Amount in rubles
    payment_type = db.Column(db.String(50), default='document', nullable=False)  # 'document'
    status = db.Column(db.String(50), default='pending', nullable=False)  # pending, completed, failed, refunded
    transaction_id = db.Column(db.String(255), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    payment_url = db.Column(db.String(500), nullable=True)  # URL for payment
    external_payment_id = db.Column(db.String(255), nullable=True)  # ID from payment provider
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)
    
    def __init__(self, user_id, amount, payment_type='document', case_id=None, description=None):
        self.user_id = user_id
        self.amount = amount
        self.payment_type = payment_type
        self.case_id = case_id
        self.description = description
    
    def mark_completed(self):
        """Mark transaction as completed."""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
    
    def mark_failed(self):
        """Mark transaction as failed."""
        self.status = 'failed'
    
    def to_dict(self):
        """Convert transaction to dictionary."""
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'amount': self.amount,
            'payment_type': self.payment_type,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'description': self.description
        }
    
    def __repr__(self):
        return f'<PaymentTransaction {self.transaction_id} {self.amount}>'


# ==================== CREDIT SYSTEM MODELS ====================

class Tariff(db.Model):
    """Тарифы системы"""
    __tablename__ = 'tariffs'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)  # single, advocate, firm, chamber
    name = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, nullable=False)  # цена в рублях
    credits = db.Column(db.Integer, nullable=False)  # количество запросов
    max_documents = db.Column(db.Integer, default=3)  # документов за раз
    clarity_requests = db.Column(db.Integer, default=0)  # внесений ясности
    has_strategy = db.Column(db.Boolean, default=False)  # стратегия защиты (только Палата)
    has_defense_speech = db.Column(db.Boolean, default=False)  # речь защиты
    has_case_audit = db.Column(db.Boolean, default=False)  # аудит судебной практики
    has_explanation_bonus = db.Column(db.Boolean, default=False)  # бонусное разъяснение
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # активен ли тариф
    description = db.Column(db.Text)
    
    # Relationships
    user_tariffs = db.relationship('UserTariff', backref='tariff', lazy='dynamic')
    
    def to_dict(self, include_savings=False):
        """Convert tariff to dictionary."""
        data = {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'price': self.price,
            'credits': self.credits,
            'max_documents': self.max_documents,
            'clarity_requests': self.clarity_requests,
            'has_strategy': self.has_strategy,
            'has_defense_speech': self.has_defense_speech,
            'has_case_audit': self.has_case_audit,
            'has_explanation_bonus': self.has_explanation_bonus,
            'is_active': self.is_active,
            'description': self.description
        }
        
        if include_savings and self.code != 'single':
            # Calculate savings vs single tariff
            single_price_per_credit = 5000  # 5000 rubles per 1 credit
            single_total = single_price_per_credit * self.credits
            savings = single_total - self.price
            percent = int((savings / single_total) * 100) if single_total > 0 else 0
            data['savings'] = {
                'vs_single': savings,
                'percent': percent
            }
        
        return data
    
    def __repr__(self):
        return f'<Tariff {self.code}: {self.name}>'


class UserTariff(db.Model):
    """Активные тарифы пользователей"""
    __tablename__ = 'user_tariffs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tariff_id = db.Column(db.Integer, db.ForeignKey('tariffs.id'), nullable=False)
    credits_total = db.Column(db.Integer, nullable=False)  # всего куплено
    credits_used = db.Column(db.Integer, default=0)  # использовано
    activated_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)  # null = не истекает
    is_active = db.Column(db.Boolean, default=True)
    
    def get_remaining_credits(self):
        """Get remaining credits."""
        return self.credits_total - self.credits_used
    
    def get_usage_percentage(self):
        """Get usage percentage."""
        if self.credits_total == 0:
            return 0
        return int((self.credits_used / self.credits_total) * 100)
    
    def get_remaining_percentage(self):
        """Get remaining percentage."""
        return 100 - self.get_usage_percentage()
    
    def use_credit(self, count=1):
        """Use credits. Returns True if successful."""
        if self.get_remaining_credits() >= count:
            self.credits_used += count
            return True
        return False
    
    def to_dict(self):
        """Convert user tariff to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'tariff_id': self.tariff_id,
            'tariff_code': self.tariff.code if self.tariff else None,
            'tariff_name': self.tariff.name if self.tariff else None,
            'credits_total': self.credits_total,
            'credits_used': self.credits_used,
            'credits_remaining': self.get_remaining_credits(),
            'percentage_remaining': self.get_remaining_percentage(),
            'activated_at': self.activated_at.isoformat() if self.activated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<UserTariff user={self.user_id} tariff={self.tariff_id}>'


class ClarityRequest(db.Model):
    """Запросы на внесение ясности"""
    __tablename__ = 'clarity_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lawyer_notes = db.Column(db.Text)  # правки юриста
    ai_learning_data = db.Column(db.Text)  # что AI запомнил
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, processed, learned
    
    # Relationships - removed dynamic from many-to-one
    case = db.relationship('Case', backref='clarity_requests_list')
    
    def to_dict(self):
        """Convert clarity request to dictionary."""
        return {
            'id': self.id,
            'case_id': self.case_id,
            'user_id': self.user_id,
            'lawyer_notes': self.lawyer_notes,
            'ai_learning_data': self.ai_learning_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'status': self.status
        }
    
    def __repr__(self):
        return f'<ClarityRequest case={self.case_id} status={self.status}>'



def init_tariffs():
    """Initialize default tariffs if not exists"""
    tariffs = [
        {
            'code': 'single', 'name': 'Разовый', 'price': 5000, 'credits': 1,
            'max_documents': 3, 'clarity_requests': 0,
            'has_explanation_bonus': True,
            'description': 'Для людей, далёких от юриспруденции. Бонусное разъяснение простым языком.'
        },
        {
            'code': 'advocate', 'name': 'Адвокат', 'price': 175000, 'credits': 50,
            'max_documents': 7, 'clarity_requests': 50,
            'description': 'Для адвокатов. Возможность внести ясность по каждому документу.'
        },
        {
            'code': 'firm', 'name': 'Фирма', 'price': 500000, 'credits': 175,
            'max_documents': 10, 'clarity_requests': 175,
            'description': 'Для юридических фирм. Экономия 18% vs тариф Адвокат.'
        },
        {
            'code': 'chamber', 'name': 'Палата', 'price': 1500000, 'credits': 500,
            'max_documents': 20, 'clarity_requests': 10,
            'has_strategy': True, 'has_defense_speech': True, 'has_case_audit': True,
            'description': 'Для адвокатских палат. Эксклюзивные фичи: стратегия защиты, речь защиты, аудит.'
        }
    ]
    
    for t in tariffs:
        if not Tariff.query.filter_by(code=t['code']).first():
            db.session.add(Tariff(**t))
    db.session.commit()


def init_db(app):
    """Initialize database with Flask app."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        init_tariffs()
