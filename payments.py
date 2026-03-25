"""
Payments and Credit System module for Legal AI Service.
Mock implementation with credit-based billing.
"""

from models import db, PaymentTransaction, Case, User, Tariff, UserTariff
from datetime import datetime, timedelta


def get_subscription_pricing():
    """Get pricing information."""
    return {
        'document_price': 5000,
        'currency': 'RUB',
        'description': 'Стоимость генерации одного юридического документа'
    }


def get_tariffs():
    """Get all available tariffs."""
    tariffs = Tariff.query.all()
    return [t.to_dict(include_savings=True) for t in tariffs]


def get_user_balance(user_id):
    """Get user's current balance across all active tariffs."""
    user_tariffs = UserTariff.query.filter_by(
        user_id=user_id, 
        is_active=True
    ).all()
    
    total_credits = sum(ut.credits_total for ut in user_tariffs)
    used_credits = sum(ut.credits_used for ut in user_tariffs)
    remaining = total_credits - used_credits
    
    # Get current tariff (most recent active)
    current_tariff = None
    if user_tariffs:
        current_ut = max(user_tariffs, key=lambda x: x.activated_at)
        current_tariff = current_ut.tariff.code if current_ut.tariff else None
    
    percentage_remaining = int((remaining / total_credits) * 100) if total_credits > 0 else 0
    
    return {
        'credits_total': total_credits,
        'credits_used': used_credits,
        'credits_remaining': remaining,
        'current_tariff': current_tariff,
        'percentage_remaining': percentage_remaining
    }


def deduct_credit(user_id, count=1):
    """Deduct credits from user's balance. Returns (success, remaining_credits)."""
    user_tariffs = UserTariff.query.filter_by(
        user_id=user_id, 
        is_active=True
    ).order_by(UserTariff.activated_at.asc()).all()
    
    # Check total available credits first
    total_available = sum(ut.get_remaining_credits() for ut in user_tariffs)
    if total_available < count:
        return False, get_user_balance(user_id)['credits_remaining']
    
    remaining_to_deduct = count
    
    for ut in user_tariffs:
        available = ut.get_remaining_credits()
        if available >= remaining_to_deduct:
            ut.credits_used += remaining_to_deduct
            remaining_to_deduct = 0
            break
        elif available > 0:
            ut.credits_used += available
            remaining_to_deduct -= available
    
    db.session.commit()
    return True, get_user_balance(user_id)['credits_remaining']


def check_balance_notifications(user_id, logger=None):
    """Check balance and send mock notifications at threshold levels."""
    from flask import current_app
    
    balance = get_user_balance(user_id)
    user = User.query.get(user_id)
    
    if not user:
        return
    
    percentage = balance['percentage_remaining']
    remaining = balance['credits_remaining']
    
    log_func = logger.info if logger else current_app.logger.info if current_app else print
    
    thresholds = [25, 15, 10, 5]
    
    for threshold in thresholds:
        if percentage <= threshold:
            log_func(f"[MOCK EMAIL] To: {user.email} | Subject: Низкий баланс кредитов ({percentage}%)")
            log_func(f"[MOCK EMAIL] Body: У вас осталось {remaining} кредитов ({percentage}%). Пополните баланс!")
            break
    
    # Check for first purchase discount offer
    if user.is_first_purchase and not user.discount_used and remaining > 0:
        log_func(f"[MOCK EMAIL] To: {user.email} | Subject: Специальное предложение - скидка 25%!")
        log_func(f"[MOCK EMAIL] Body: Вы оплатили первый раз! Получите скидку 25% на тарифы 'Фирма' и 'Палата'!")
        log_func(f"[MOCK EMAIL] Promo code: FIRST25")


def mock_topup(user_id, tariff_code, amount=None):
    """
    Mock balance top-up (no real payment).
    
    Args:
        user_id: User ID
        tariff_code: Code of tariff to purchase
        amount: Amount in rubles (optional, for custom amounts)
    
    Returns:
        Tuple of (success, result_dict)
    """
    tariff = Tariff.query.filter_by(code=tariff_code).first()
    if not tariff:
        return False, {'error': 'Тариф не найден', 'message': 'Tariff not found'}
    
    # Deactivate any existing active tariffs for this user
    existing_tariffs = UserTariff.query.filter_by(user_id=user_id, is_active=True).all()
    for et in existing_tariffs:
        et.is_active = False
    
    # Create new user tariff
    user_tariff = UserTariff(
        user_id=user_id,
        tariff_id=tariff.id,
        credits_total=tariff.credits,
        credits_used=0,
        is_active=True
    )
    db.session.add(user_tariff)
    
    # Update first purchase status
    user = User.query.get(user_id)
    if user and user.is_first_purchase:
        user.is_first_purchase = False
    
    db.session.commit()
    
    balance = get_user_balance(user_id)
    
    return True, {
        'message': f'Тариф "{tariff.name}" активирован',
        'tariff': tariff.to_dict(),
        'balance': balance
    }


def process_analysis_payment(user_id, case_id, payment_method='card'):
    """
    Process payment for case analysis.
    Mock implementation - always succeeds.
    
    Args:
        user_id: User ID
        case_id: Case ID
        payment_method: Payment method (default: 'card')
    
    Returns:
        Tuple of (success, result_dict)
    """
    case = Case.query.get(case_id)
    if not case:
        return False, {'error': 'Case not found', 'message': 'Дело не найдено'}
    
    if case.user_id != user_id:
        return False, {'error': 'Access denied', 'message': 'Доступ запрещен'}
    
    if case.paid:
        return True, {'message': 'Already paid', 'case_id': case_id}
    
    # Create transaction
    transaction = PaymentTransaction(
        user_id=user_id,
        case_id=case_id,
        amount=case.price,
        payment_type='document',
        payment_method=payment_method,
        description=f'Оплата документа: {case.case_title}'
    )
    db.session.add(transaction)
    
    # Mark case as paid
    case.mark_as_paid()
    db.session.commit()
    
    return True, {
        'transaction_id': transaction.transaction_id,
        'amount': case.price,
        'case_id': case_id,
        'status': 'completed'
    }


def get_payment_history(user_id, limit=20, offset=0):
    """
    Get user's payment history.
    
    Args:
        user_id: User ID
        limit: Number of records to return
        offset: Offset for pagination
    
    Returns:
        List of transaction dictionaries
    """
    transactions = PaymentTransaction.query.filter_by(user_id=user_id)\
        .order_by(PaymentTransaction.created_at.desc())\
        .limit(limit).offset(offset).all()
    
    return [t.to_dict() for t in transactions]


def check_rate_limit(user_id, ip_address, max_requests=200, days=30):
    """
    Check if user can make a request based on rate limits.
    Mock implementation - always allows.
    
    Returns:
        Tuple of (allowed, remaining, reset_date)
    """
    from models import IPRequest
    
    count = IPRequest.get_request_count(user_id, ip_address, days)
    allowed = count < max_requests
    remaining = max_requests - count
    reset_date = datetime.utcnow() + timedelta(days=days)
    
    return allowed, remaining, reset_date


def record_ip_request(user_id, ip_address, request_type):
    """Record IP request for rate limiting."""
    from models import IPRequest
    
    request = IPRequest(
        user_id=user_id,
        ip_address=ip_address,
        request_type=request_type
    )
    db.session.add(request)
    db.session.commit()
    return request
