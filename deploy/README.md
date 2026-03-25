# Legal AI Service - Deployment Guide

Полное руководство по развёртыванию юридического AI-сервиса на сервере.

## 📋 Содержание

- [Требования](#требования)
- [Быстрое развёртывание](#быстрое-развёртывание)
- [Пошаговая установка](#пошаговая-установка)
- [Конфигурация](#конфигурация)
- [SSL сертификаты](#ssl-сертификаты)
- [Управление сервисом](#управление-сервисом)
- [Мониторинг и логи](#мониторинг-и-логи)
- [Устранение неполадок](#устранение-неполадок)

## 🔧 Требования

### Минимальные системные требования:
- **OS**: Ubuntu 20.04+ / Debian 11+
- **RAM**: 2 GB
- **CPU**: 2 ядра
- **Диск**: 20 GB SSD
- **Порты**: 80 (HTTP), 443 (HTTPS), 22 (SSH)

### Необходимое ПО:
- Python 3.8+
- Nginx
- Git
- curl

## 🚀 Быстрое развёртывание

### 1. Автоматическая установка

```bash
# Скопируйте проект на сервер
cd /mnt/okcomputer/output/legal-ai-service/deploy

# Запустите скрипт развёртывания (без SSL)
sudo bash deploy.sh

# Или с указанием домена
sudo bash deploy.sh --domain your-domain.com

# С SSL (только для реальных доменов)
sudo bash deploy.sh --domain your-domain.com --ssl
```

### 2. Настройка переменных окружения

```bash
# Отредактируйте файл с переменными окружения
sudo nano /var/www/legal-ai-service/.env
```

Обязательно укажите:
- `KIMI_API_KEY` - ваш API ключ Kimi AI
- `SECRET_KEY` - секретный ключ для Flask
- `STRIPE_SECRET_KEY` - ключ Stripe для платежей (опционально)

### 3. Перезапуск сервиса

```bash
sudo systemctl restart legal-ai
```

## 📖 Пошаговая установка

### Шаг 1: Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка зависимостей
sudo apt install -y python3 python3-pip python3-venv nginx git curl
```

### Шаг 2: Создание директории приложения

```bash
# Создание директории
sudo mkdir -p /var/www/legal-ai-service

# Копирование файлов
sudo cp -r /mnt/okcomputer/output/legal-ai-service/* /var/www/legal-ai-service/

# Создание необходимых директорий
sudo mkdir -p /var/www/legal-ai-service/uploads
sudo mkdir -p /var/log/legal-ai
```

### Шаг 3: Создание виртуального окружения

```bash
cd /var/www/legal-ai-service

# Создание venv
sudo python3 -m venv venv

# Активация и установка зависимостей
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

deactivate
```

### Шаг 4: Настройка переменных окружения

```bash
# Копирование шаблона
sudo cp /var/www/legal-ai-service/deploy/.env.example /var/www/legal-ai-service/.env

# Редактирование
sudo nano /var/www/legal-ai-service/.env
```

Заполните следующие переменные:
```bash
KIMI_API_KEY=your_actual_kimi_api_key
SECRET_KEY=your_random_secret_key
FLASK_ENV=production
```

### Шаг 5: Настройка systemd сервиса

```bash
# Копирование конфигурации сервиса
sudo cp /var/www/legal-ai-service/deploy/legal-ai.service /etc/systemd/system/

# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable legal-ai

# Запуск сервиса
sudo systemctl start legal-ai
```

### Шаг 6: Настройка Nginx

```bash
# Удаление дефолтного конфига
sudo rm -f /etc/nginx/sites-enabled/default

# Копирование конфигурации (HTTP только)
sudo cp /var/www/legal-ai-service/deploy/nginx-http-only.conf /etc/nginx/sites-available/legal-ai

# Или с SSL (после получения сертификата)
# sudo cp /var/www/legal-ai-service/deploy/nginx.conf /etc/nginx/sites-available/legal-ai

# Создание симлинка
sudo ln -sf /etc/nginx/sites-available/legal-ai /etc/nginx/sites-enabled/

# Проверка конфигурации
sudo nginx -t

# Перезагрузка Nginx
sudo systemctl restart nginx
```

### Шаг 7: Настройка firewall

```bash
# Установка UFW (если не установлен)
sudo apt install -y ufw

# Настройка правил
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS

# Включение firewall
sudo ufw --force enable

# Проверка статуса
sudo ufw status verbose
```

## 🔐 SSL сертификаты

### Автоматическая настройка с Let's Encrypt

```bash
# Установка Certbot
sudo apt install -y certbot python3-certbot-nginx

# Получение сертификата
sudo certbot --nginx -d your-domain.com

# Автоматическое обновление
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### Использование скрипта SSL

```bash
cd /var/www/legal-ai-service/deploy
sudo bash ssl-setup.sh --domain your-domain.com --email admin@your-domain.com
```

### Ручная настройка SSL

```bash
# Получение сертификата
sudo certbot certonly --standalone -d your-domain.com

# Обновление Nginx конфигурации
sudo cp /var/www/legal-ai-service/deploy/nginx.conf /etc/nginx/sites-available/legal-ai
sudo sed -i 's/legal-ai-service.local/your-domain.com/g' /etc/nginx/sites-available/legal-ai

# Перезагрузка Nginx
sudo nginx -t && sudo systemctl reload nginx
```

### Проверка обновления сертификата

```bash
# Тестовый запуск обновления
sudo certbot renew --dry-run

# Ручное обновление
sudo certbot renew
```

## ⚙️ Конфигурация

### Структура конфигурационных файлов

```
/etc/systemd/system/legal-ai.service    # Systemd сервис
/etc/nginx/sites-available/legal-ai     # Nginx конфигурация
/var/www/legal-ai-service/.env          # Переменные окружения
/var/log/legal-ai/                      # Логи приложения
/var/log/nginx/                         # Логи Nginx
```

### Переменные окружения (.env)

| Переменная | Описание | Обязательная |
|------------|----------|--------------|
| `KIMI_API_KEY` | API ключ Kimi AI | Да |
| `SECRET_KEY` | Секретный ключ Flask | Да |
| `FLASK_ENV` | Режим работы (production) | Да |
| `DATABASE_URL` | URL базы данных | Нет |
| `STRIPE_SECRET_KEY` | Ключ Stripe | Нет |
| `MAIL_SERVER` | SMTP сервер | Нет |

## 🎛️ Управление сервисом

### Systemd команды

```bash
# Проверка статуса
sudo systemctl status legal-ai

# Запуск
sudo systemctl start legal-ai

# Остановка
sudo systemctl stop legal-ai

# Перезапуск
sudo systemctl restart legal-ai

# Просмотр логов
sudo journalctl -u legal-ai -f

# Просмотр всех логов
sudo journalctl -u legal-ai --no-pager
```

### Nginx команды

```bash
# Проверка статуса
sudo systemctl status nginx

# Проверка конфигурации
sudo nginx -t

# Перезагрузка
sudo systemctl reload nginx

# Перезапуск
sudo systemctl restart nginx
```

### Управление через скрипты

```bash
# Остановка всех сервисов
sudo bash /var/www/legal-ai-service/deploy/manage.sh stop

# Запуск всех сервисов
sudo bash /var/www/legal-ai-service/deploy/manage.sh start

# Перезапуск
sudo bash /var/www/legal-ai-service/deploy/manage.sh restart

# Статус
sudo bash /var/www/legal-ai-service/deploy/manage.sh status
```

## 📊 Мониторинг и логи

### Логи приложения

```bash
# Логи systemd
sudo journalctl -u legal-ai -f

# Логи доступа
sudo tail -f /var/log/legal-ai/access.log

# Логи ошибок
sudo tail -f /var/log/legal-ai/error.log
```

### Логи Nginx

```bash
# Access log
sudo tail -f /var/log/nginx/legal-ai-access.log

# Error log
sudo tail -f /var/log/nginx/legal-ai-error.log
```

### Мониторинг ресурсов

```bash
# Использование памяти
free -h

# Использование диска
df -h

# Процессы
htop

# Сетевые соединения
ss -tlnp
```

### Health Check

```bash
# Проверка работоспособности
curl http://localhost/health

# Проверка через Nginx
curl http://your-domain.com/health
```

## 🐛 Устранение неполадок

### Сервис не запускается

```bash
# Проверка статуса
sudo systemctl status legal-ai

# Просмотр логов
sudo journalctl -u legal-ai --no-pager | tail -50

# Проверка прав
sudo ls -la /var/www/legal-ai-service/
sudo chown -R www-data:www-data /var/www/legal-ai-service/
```

### Ошибки Nginx

```bash
# Проверка конфигурации
sudo nginx -t

# Просмотр логов
sudo tail -f /var/log/nginx/error.log

# Проверка портов
sudo ss -tlnp | grep :80
sudo ss -tlnp | grep :443
```

### Проблемы с SSL

```bash
# Проверка сертификата
sudo certbot certificates

# Тест обновления
sudo certbot renew --dry-run

# Пересоздание сертификата
sudo certbot delete --cert-name your-domain.com
sudo certbot --nginx -d your-domain.com
```

### Ошибки приложения

```bash
# Проверка виртуального окружения
ls -la /var/www/legal-ai-service/venv/

# Переустановка зависимостей
cd /var/www/legal-ai-service
source venv/bin/activate
pip install -r requirements.txt

# Проверка переменных окружения
cat /var/www/legal-ai-service/.env
```

### Порт 5000 занят

```bash
# Поиск процесса
sudo lsof -i :5000

# Завершение процесса
sudo kill -9 <PID>

# Или изменение порта в конфигурации
```

## 🔒 Безопасность

### Рекомендации по безопасности

1. **Обновляйте систему регулярно**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Используйте сложные пароли** для всех сервисов

3. **Настройте fail2ban** для защиты от брутфорса:
   ```bash
   sudo apt install -y fail2ban
   sudo systemctl enable fail2ban
   sudo systemctl start fail2ban
   ```

4. **Отключите вход по паролю для SSH** (используйте ключи)

5. **Регулярно проверяйте логи** на подозрительную активность

6. **Обновляйте SSL сертификаты** (автоматически через cron)

## 📁 Файлы развёртывания

```
deploy/
├── legal-ai.service          # Systemd конфигурация
├── nginx.conf                # Nginx конфигурация с SSL
├── nginx-http-only.conf      # Nginx конфигурация без SSL
├── .env.example              # Шаблон переменных окружения
├── deploy.sh                 # Скрипт автоматического развёртывания
├── ssl-setup.sh              # Скрипт настройки SSL
├── manage.sh                 # Скрипт управления сервисом
└── README.md                 # Это руководство
```

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `sudo journalctl -u legal-ai -f`
2. Проверьте статус сервисов: `sudo systemctl status legal-ai nginx`
3. Проверьте конфигурацию Nginx: `sudo nginx -t`

## 📄 Лицензия

Этот проект распространяется под лицензией MIT.
