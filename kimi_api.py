"""
Модуль интеграции с API Кими (Moonshot AI) для юридического сервиса.
РЕАЛЬНАЯ ВЕРСИЯ с API запросами.

Предоставляет функции для:
- Анализа документов дела
- Генерации юридических документов
- Проверки согласованности контекста
"""

import json
import time
import requests
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация API
API_BASE_URL = "https://api.moonshot.ai/v1"
API_KEY = "sk-kUpcQ7a7hqbcXEeJSGbV2n9AGzyM4ECHrr5o7bA8R6lGGzTn"
DEFAULT_MODEL = "moonshot-v1-8k"
MAX_RETRIES = 3
TIMEOUT = 90


class DocumentType(Enum):
    """Типы юридических документов."""
    COMPLAINT = "complaint"      # Исковое заявление
    APPEAL = "appeal"            # Апелляционная жалоба
    PETITION = "petition"        # Претензия
    STATEMENT = "statement"      # Стратегия защиты


class KimiAPIError(Exception):
    """Базовое исключение для ошибок API Кими."""
    pass


class RateLimitError(KimiAPIError):
    """Исключение при превышении лимита запросов."""
    pass


class AuthenticationError(KimiAPIError):
    """Исключение при ошибке аутентификации."""
    pass


def _make_api_request(messages: List[Dict[str, str]], temperature: float = 0.3, max_tokens: int = 4000) -> str:
    """
    Внутренняя функция для выполнения API запроса к Moonshot AI.
    
    Args:
        messages: Список сообщений в формате [{"role": "system"/"user", "content": "..."}]
        temperature: Температура генерации (0.0 - 1.0)
        max_tokens: Максимальное количество токенов в ответе
        
    Returns:
        Текст ответа от API
        
    Raises:
        KimiAPIError: При ошибке API
        RateLimitError: При превышении лимита запросов
        AuthenticationError: При ошибке аутентификации
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    payload = {
        "model": DEFAULT_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"API запрос (попытка {attempt + 1}/{MAX_RETRIES})")
            response = requests.post(
                f"{API_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=TIMEOUT
            )
            
            if response.status_code == 401:
                raise AuthenticationError("Ошибка аутентификации. Проверьте API ключ.")
            elif response.status_code == 429:
                raise RateLimitError("Превышен лимит запросов. Попробуйте позже.")
            elif response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                raise KimiAPIError(f"Ошибка API: {error_msg}")
            
            data = response.json()
            content = data['choices'][0]['message']['content']
            logger.info(f"API ответ получен, длина: {len(content)} символов")
            return content
            
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES - 1:
                wait_time = (attempt + 1) * 2
                logger.warning(f"Таймаут, повтор через {wait_time} сек...")
                time.sleep(wait_time)
            else:
                raise KimiAPIError("Превышено время ожидания ответа от API")
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = (attempt + 1) * 2
                logger.warning(f"Ошибка сети: {e}, повтор через {wait_time} сек...")
                time.sleep(wait_time)
            else:
                raise KimiAPIError(f"Ошибка сети: {e}")
    
    raise KimiAPIError("Не удалось выполнить запрос после всех попыток")


def analyze_case_documents(documents_text: List[str], api_key: str = None) -> Dict[str, Any]:
    """
    Анализирует документы по делу и возвращает структурированный отчет.
    
    Args:
        documents_text: Список текстов документов для анализа
        api_key: API ключ (не используется, оставлен для совместимости)
        
    Returns:
        Словарь с результатами анализа
    """
    if not documents_text:
        raise ValueError("Список документов не может быть пустым")
    
    logger.info(f"Анализ {len(documents_text)} документов через Moonshot AI")
    
    # Формируем промпт для анализа
    documents_combined = "\n\n---\n\n".join([
        f"ДОКУМЕНТ {i+1}:\n{doc}" 
        for i, doc in enumerate(documents_text)
    ])
    
    system_prompt = """Ты — профессиональный юрист-аналитик. Проанализируй предоставленные документы по делу и составь структурированный отчет.

Ответ должен быть в формате JSON со следующими полями:
- document_list: список документов с кратким описанием каждого
- legal_summary: краткое юридическое заключение по существу дела
- collisions: список юридических коллизий (вопросов, требующих уточнения)
- contradictions: список противоречий между документами
- recommendations: список рекомендаций по дальнейшим действиям

Отвечай только JSON, без дополнительного текста."""

    user_prompt = f"Проанализируй следующие документы по делу:\n\n{documents_combined}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        response = _make_api_request(messages, temperature=0.2, max_tokens=3000)
        
        # Пытаемся распарсить JSON из ответа
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # Если JSON не распарсился, пробуем извлечь из markdown блока
            if "```json" in response:
                json_text = response.split("```json")[1].split("```")[0].strip()
                result = json.loads(json_text)
            elif "```" in response:
                json_text = response.split("```")[1].split("```")[0].strip()
                result = json.loads(json_text)
            else:
                raise KimiAPIError(f"Не удалось распарсить JSON ответ: {response[:200]}")
        
        # Обеспечиваем наличие всех обязательных полей
        return {
            "document_list": result.get("document_list", []),
            "legal_summary": result.get("legal_summary", ""),
            "collisions": result.get("collisions", []),
            "contradictions": result.get("contradictions", []),
            "recommendations": result.get("recommendations", [])
        }
        
    except Exception as e:
        logger.error(f"Ошибка при анализе документов: {e}")
        # Возвращаем базовую структуру в случае ошибки
        return {
            "document_list": [f"Документ {i+1}" for i in range(len(documents_text))],
            "legal_summary": "Анализ не удался. Пожалуйста, попробуйте позже.",
            "collisions": [],
            "contradictions": [str(e)],
            "recommendations": ["Повторите запрос или обратитесь в поддержку"]
        }


def generate_legal_document(
    case_data: Dict[str, Any], 
    document_type: str, 
    api_key: str = None
) -> str:
    """
    Генерирует юридический документ через Moonshot AI.
    
    Args:
        case_data: Данные дела для генерации документа
        document_type: Тип документа ('complaint', 'appeal', 'petition', 'statement')
        api_key: API ключ (не используется, оставлен для совместимости)
        
    Returns:
        Текст сгенерированного юридического документа
    """
    if not case_data:
        raise ValueError("Данные дела не могут быть пустыми")
    
    # Преобразуем строковый тип в enum
    try:
        doc_type = DocumentType(document_type.lower())
    except ValueError:
        valid_types = [t.value for t in DocumentType]
        raise ValueError(f"Недопустимый тип документа. Допустимые значения: {valid_types}")
    
    logger.info(f"Генерация документа типа: {doc_type.value} через Moonshot AI")
    
    # Формируем системный промпт в зависимости от типа документа
    doc_type_prompts = {
        DocumentType.COMPLAINT: """Ты — профессиональный юрист. Составь исковое заявление по договору займа.
Используй официальный юридический стиль, ссылки на статьи ГК РФ и ГПК РФ.
Документ должен быть полным, грамотным и соответствовать требованиям процессуального законодательства РФ.""",
        
        DocumentType.APPEAL: """Ты — профессиональный юрист. Составь апелляционную жалобу.
Используй официальный юридический стиль, ссылки на статьи ГПК РФ.
Документ должен содержать ссылки на нарушения закона и необоснованность решения суда первой инстанции.""",
        
        DocumentType.PETITION: """Ты — профессиональный юрист. Составь досудебную претензию.
Используй строгий, но корректный стиль. Документ должен содержать ссылки на нарушения договора и требования о добровольном исполнении обязательств.""",
        
        DocumentType.STATEMENT: """Ты — профессиональный юрист. Составь стратегию защиты в суде.
Документ должен включать анализ дела, правовое обоснование, тактику защиты, календарный план и оценку рисков."""
    }
    
    system_prompt = doc_type_prompts.get(doc_type, doc_type_prompts[DocumentType.COMPLAINT])
    
    # Формируем данные для подстановки
    case_json = json.dumps(case_data, ensure_ascii=False, indent=2)
    
    doc_type_names = {
        "complaint": "исковое заявление",
        "appeal": "апелляционную жалобу",
        "petition": "претензию",
        "statement": "стратегию защиты"
    }
    
    user_prompt = f"""Составь {doc_type_names.get(document_type.lower(), 'документ')} на основе следующих данных дела:

{case_json}

Требования:
1. Используй предоставленные данные для заполнения всех полей
2. Соблюдай структуру документа согласно законодательству РФ
3. Включи ссылки на соответствующие статьи законов
4. Используй официальный юридический язык
5. Документ должен быть готов к подаче (без плейсхолдеров типа [ФИО])

Выдай только текст документа, без дополнительных комментариев."""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        response = _make_api_request(messages, temperature=0.3, max_tokens=4000)
        return response.strip()
        
    except Exception as e:
        logger.error(f"Ошибка при генерации документа: {e}")
        raise KimiAPIError(f"Не удалось сгенерировать документ: {e}")


def check_context_consistency(documents: List[str], api_key: str = None) -> Dict[str, Any]:
    """
    Проверяет согласованность контекста между документами.
    
    Args:
        documents: Список текстов документов для проверки
        api_key: API ключ (не используется, оставлен для совместимости)
        
    Returns:
        Словарь с результатами проверки
    """
    if not documents or len(documents) < 2:
        raise ValueError("Для проверки согласованности требуется минимум 2 документа")
    
    logger.info(f"Проверка согласованности {len(documents)} документов через Moonshot AI")
    
    documents_combined = "\n\n---\n\n".join([
        f"ДОКУМЕНТ {i+1}:\n{doc[:2000]}"  # Ограничиваем длину каждого документа
        for i, doc in enumerate(documents)
    ])
    
    system_prompt = """Ты — профессиональный юрист-аналитик. Проверь согласованность контекста между предоставленными документами.

Ответ должен быть в формате JSON:
{
  "consistent": true/false,
  "issues": ["описание проблемы 1", "описание проблемы 2", ...]
}

Если документы согласованы — issues должен быть пустым массивом.
Отвечай только JSON, без дополнительного текста."""

    user_prompt = f"Проверь согласованность следующих документов:\n\n{documents_combined}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        response = _make_api_request(messages, temperature=0.2, max_tokens=2000)
        
        # Пытаемся распарсить JSON
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            if "```json" in response:
                json_text = response.split("```json")[1].split("```")[0].strip()
                result = json.loads(json_text)
            elif "```" in response:
                json_text = response.split("```")[1].split("```")[0].strip()
                result = json.loads(json_text)
            else:
                raise KimiAPIError(f"Не удалось распарсить JSON: {response[:200]}")
        
        return {
            "consistent": result.get("consistent", True),
            "issues": result.get("issues", [])
        }
        
    except Exception as e:
        logger.error(f"Ошибка при проверке согласованности: {e}")
        return {
            "consistent": True,
            "issues": [f"Ошибка проверки: {str(e)}"]
        }


# =============================================================================
# УТИЛИТЫ
# =============================================================================

def get_document_type_name(doc_type: str) -> str:
    """Возвращает русское название типа документа."""
    names = {
        'complaint': 'Исковое заявление',
        'appeal': 'Апелляционная жалоба',
        'petition': 'Претензия',
        'statement': 'Стратегия защиты в суде'
    }
    return names.get(doc_type.lower(), 'Документ')


def get_document_type_enum(doc_type: str) -> Optional[DocumentType]:
    """Преобразует строковый тип в enum."""
    try:
        return DocumentType(doc_type.lower())
    except ValueError:
        return None


def test_api_connection() -> Dict[str, Any]:
    """
    Тестирует подключение к API Moonshot.
    
    Returns:
        Словарь с результатом теста
    """
    try:
        messages = [
            {"role": "system", "content": "Ты — помощник. Ответь кратко."},
            {"role": "user", "content": "Привет! Проверка связи. Какая сегодня дата?"}
        ]
        response = _make_api_request(messages, temperature=0.7, max_tokens=100)
        return {
            "success": True,
            "response": response,
            "model": DEFAULT_MODEL
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# =============================================================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MOONSHOT AI API - ТЕСТИРОВАНИЕ")
    print("=" * 70)
    
    # Тест 0: Проверка подключения
    print("\n>>> Тест 0: Проверка подключения к API")
    print("-" * 50)
    
    result = test_api_connection()
    if result["success"]:
        print(f"✓ Подключение успешно")
        print(f"  Модель: {result['model']}")
        print(f"  Ответ: {result['response'][:100]}...")
    else:
        print(f"✗ Ошибка подключения: {result['error']}")
        exit(1)
    
    # Тест 1: Анализ документов
    print("\n>>> Тест 1: Анализ документов")
    print("-" * 50)
    
    test_docs = [
        "Договор займа от 15.01.2024 на сумму 100000 руб. между Ивановым И.И. и Петровым П.П.",
        "Расписка в получении денежных средств от 15.01.2024 на сумму 100000 руб.",
        "Требование об уплате долга от 01.03.2024 с уведомлением о намерении обратиться в суд"
    ]
    
    try:
        result = analyze_case_documents(test_docs)
        print(f"✓ Анализ выполнен")
        print(f"  Документов: {len(result['document_list'])}")
        print(f"  Противоречий: {len(result['contradictions'])}")
        print(f"  Рекомендаций: {len(result['recommendations'])}")
        print(f"  Заключение: {result['legal_summary'][:200]}...")
    except Exception as e:
        print(f"✗ Ошибка: {e}")
    
    # Тест 2: Генерация искового заявления
    print("\n>>> Тест 2: Генерация искового заявления")
    print("-" * 50)
    
    test_case_data = {
        'court_name': 'Мировой судья судебного участка № 123 района города Москвы',
        'plaintiff': {
            'name': 'Иванов Иван Иванович',
            'address': 'г. Москва, ул. Ленина, д. 10, кв. 50'
        },
        'defendant': {
            'name': 'Петров Петр Петрович',
            'address': 'г. Москва, ул. Пушкина, д. 5, кв. 12'
        },
        'claim_amount': '103 500',
        'date': '15.01.2024',
        'loan_amount': '100 000',
        'due_date': '15.04.2024',
        'date_today': '"15" марта 2025 г.',
        'interest_amount': '3000',
        'penalty_amount': '500',
        'court_fee': '2000',
        'lawyer_fee': '10000',
        'total_expenses': '12000',
        'moral_damage': '0'
    }
    
    try:
        document = generate_legal_document(test_case_data, 'complaint')
        print(f"✓ Документ сгенерирован")
        print(f"  Длина: {len(document)} символов")
        print(f"  Первые 300 символов:\n{document[:300]}...")
    except Exception as e:
        print(f"✗ Ошибка: {e}")
    
    # Тест 3: Проверка согласованности
    print("\n>>> Тест 3: Проверка согласованности")
    print("-" * 50)
    
    try:
        result = check_context_consistency(test_docs)
        print(f"✓ Проверка выполнена")
        print(f"  Согласованность: {'Да' if result['consistent'] else 'Нет'}")
        if result['issues']:
            print(f"  Проблемы: {result['issues']}")
    except Exception as e:
        print(f"✗ Ошибка: {e}")
    
    print("\n" + "=" * 70)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 70)
