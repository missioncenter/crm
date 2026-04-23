# CRM Local MVP

Проект — минимальный проектный менеджер на Django с Kanban-доской, CRUD для проектов/задач/пользователей и Single-Container инфраструктурой на Docker.

Этот репозиторий содержит рабочий прототип. Внизу есть подробный анализ проекта и рекомендации в [ANALYSIS.md](ANALYSIS.md).

## Краткий обзор

- Стек: Django + SQLite (по умолчанию), Nginx + Gunicorn под supervisord
- Статические файлы собираются через `collectstatic` в `staticfiles/`
- Канбан-интерфейс реализован в `projects` (JS + AJAX)

## Структура проекта (основное)

- `Dockerfile` — образ на `python:3.12-slim`
- `supervisord.conf` — запуск `gunicorn` + `nginx`
- `nginx.conf` — проксирование и выдача `static`/`media`
- `manage.py` — Django CLI
- `crm_local/` — настройки, URLs, WSGI
- `projects/` — основное приложение: модели, формы, представления, шаблоны, static

## Быстрый локальный запуск (Windows)

1. Откройте PowerShell в корне проекта.
2. Создайте виртуальную среду:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Установите зависимости:

```powershell
pip install -r requirements.txt
```

4. Выполните миграции и создайте суперпользователя:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

5. Запустите локально (dev):

```powershell
python manage.py runserver 9090
```

6. Откройте в браузере `http://127.0.0.1:9090/`.

## Docker (сборка и запуск)

Соберите образ:

```powershell
docker build -t crm-local-mvp .
```

Запустите контейнер:

```powershell
docker run -d --name crm-local-mvp \
  -p 9090:9090 \
  -v "%cd%\db.sqlite3:/app/db.sqlite3" \
  -v "%cd%\media:/app/media" \
  crm-local-mvp
```

## Куда смотреть в коде

- Основные модели и права: [projects/models.py](projects/models.py)
- Представления и логика UI: [projects/views.py](projects/views.py)
- Формы: [projects/forms.py](projects/forms.py)
- URL-маршруты: [projects/urls.py](projects/urls.py)
- Настройки: [crm_local/settings.py](crm_local/settings.py)

## Короткие рекомендации

- Убрать `SECRET_KEY` из `settings.py` и загружать из окружения.
- Переключить на PostgreSQL для продакшн; не хранить prod данные в SQLite.
- В `Dockerfile` и `requirements.txt` — зафиксировать версии зависимостей и добавить `pip-tools`/`constraints.txt`.
- Отключать `DEBUG` в продакшне и правильно настроить `ALLOWED_HOSTS`.
- Добавить тесты (pytest-django), линтер (ruff/flake8) и pre-commit hooks.

Полный анализ с деталями, проблемами и шагами исправления — в [ANALYSIS.md](ANALYSIS.md).

## Переменные окружения

Для удобства и безопасности приложение должно считывать конфигурацию из окружения. Рекомендуемые переменные (пример в `.env.example`):

- `DJANGO_SECRET_KEY` — секретный ключ Django (обязательно для продакшна)
- `DJANGO_DEBUG` — `1` или `0` (по умолчанию для локальной разработки можно `1`)
- `DATABASE_URL` — URL базы данных (например `sqlite:///db.sqlite3` или `postgres://...`)
- `ALLOWED_HOSTS` — список хостов через запятую (для продакшн)
- `PORT` — порт запуска приложения в контейнере (по умолчанию `9090`)

В `crm_local/settings.py` рекомендуется использовать чтение через `os.environ` или `django-environ`.

## Тесты

Проекта пока нет тестов. Рекомендации для добавления тестовой среды:

- Установить `pytest` и `pytest-django`.
- Создать `pytest.ini` с настройками Django-проекта.
- Добавлять простые unit/functional тесты для моделей и view.

Запуск (после установки тест-зависимостей):

```powershell
pip install pytest pytest-django
pytest -q
```

## Разработка

Локальные шаги для разработки и отладки:

1. Создать виртуальное окружение и установить зависимости (см. выше).
2. Экспортировать переменные окружения или создать `.env` на основе `.env.example`.
3. Выполнить миграции: `python manage.py migrate`.
4. Создать суперпользователя: `python manage.py createsuperuser`.
5. Запуск сервера разработки: `python manage.py runserver 0.0.0.0:9090`.

## Вклад и стиль кода

См. `CONTRIBUTING.md` для правил оформления PR, линтинга и тестов.

---

Если нужно, могу сформировать `docker-compose.yml`, CI workflow и шаблон `.env`.
