
# Анализ проекта — CRM Local MVP

Дата: 2026-04-22

Краткое описание: проект — минимальный проектный менеджер на Django с одним приложением `projects`, использующий SQLite по умолчанию и single-container Docker (nginx + gunicorn + supervisord).

---

## Обзор найденных артефактов

- Основные директории:
  - `crm_local/` — настройки и точки входа
  - `projects/` — модели, формы, views, templates, static
  - `staticfiles/` — целевая директория для `collectstatic` (настроена в `settings.py`)
- Docker: `Dockerfile`, `nginx.conf`, `supervisord.conf` присутствуют и обеспечивают single-container запуск
- Зависимости: `requirements.txt` (не зафиксированные версии, указаны диапазоны)

## Основные риски и замечания

1) Секьюрность конфигурации
- `SECRET_KEY` хранится в `crm_local/settings.py` в явном виде — опасно для публичных репозиториев.
- `DEBUG = True` и `ALLOWED_HOSTS = ["*"]` в настройках — недопустимо для продакшн.
- Использование SQLite в образе/контейнере не подходит для многопользовательского продакшна.

Рекомендации:
- Выносить `SECRET_KEY`, `DEBUG`, `DATABASE_URL` и другие секреты в переменные окружения (использовать `django-environ` или `python-decouple`).
- В проде установить `DEBUG=False` и явно задать `ALLOWED_HOSTS`.
- Перейти на PostgreSQL в продакшне; в Docker Compose подключить named volume для БД.

2) Управление зависимостями
- `requirements.txt` использует диапазоны, лучше зафиксировать конкретные версии и/или генерировать `requirements.txt` через `pip-tools`.

Рекомендации:
- Использовать `pip-tools` (`requirements.in` + `pip-compile`) или `poetry`/`pipenv`.
- Добавить `requirements-dev.txt` с инструментами: `pytest`, `pytest-django`, `ruff`/`flake8`, `black`, `pre-commit`.

3) Отсутствие тестов и CI
- В репозитории нет тестов; нет конфигурации CI.

Рекомендации:
- Добавить модульные тесты (pytest + pytest-django), покрыть модели и ключевые view (авторизация, CRUD).
- Подключить GitHub Actions с прогоном тестов, линтера и format check.

4) Код и производительность
- В большинстве view используются селекты с `select_related` и `prefetch_related` — хорошо для уменьшения N+1.
- Некоторая логика прав распределена по хелперам в `views.py` и моделям — читабельно, но стоит пересмотреть расположение бизнес-логики (часть можно вынести в сервисы).

Рекомендации:
- Провести статический анализ (ruff/flake8, mypy если вводить typing).
- Вынести повторы (проверки ролей/прав) в отдельный модуль `projects/permissions.py`.

5) Docker и развёртывание
- Single-container подход работает для демо, но продакшн лучше разбивать на несколько контейнеров (web, db, nginx).
- `Dockerfile` собирает контейнер и запускает collectstatic во время билда — нормально, но учтите, что при изменениях статических файлов нужно пересобирать образ.

Рекомендации:
- Добавить `docker-compose.yml` с сервисами: `web`, `db` (Postgres), `nginx`. Это упростит локальную разработку.
- Рассмотреть использование entrypoint-скрипта, управляющего миграциями и созданием superuser при старте.

6) Статические и медиа файлы
- `staticfiles` и `media` монтируются/обслуживаются через nginx — хорошо.
- В `.gitignore` уже исключены `db.sqlite3`, `media` и `staticfiles`.

7) UI/шаблоны
- Шаблоны есть в `projects/templates/` — следует проверить XSS в местах, где шаблоны выводят пользовательский ввод (Django эскейпит по умолчанию).

8) Прочее
- `supervisord.conf` запускает gunicorn и nginx вместе — работает в контейнере.
- Логи идут в stdout/stderr — удобно для контейнеров.

---

## План улучшений (приоритеты)

1. Критично (prod-ready):
  - Вынести секреты в переменные окружения; переключить DEBUG в False.
  - Перейти на PostgreSQL в продакшне.
  - Зафиксировать версии зависимостей.

2. Средний приоритет:
  - Добавить тесты (pytest-django). Покрыть минимум CRUD и проверки прав.
  - Добавить CI (GitHub Actions): lint → tests → build image.
  - Добавить pre-commit hooks (ruff/black).

3. Долгосрочно:
  - Распаковать монолитный контейнер в compose-сеть (web/db/nginx)
  - Улучшить архитектуру: сервисы для бизнес-логики, вынос permissions.

---

## Быстрые шаги для разработчика (команды)

1) Зафиксировать зависимости (пример с pip-tools):

```bash
pip install pip-tools
pip-compile --output-file=requirements.txt requirements.in
```

2) Вынести конфигурацию из `settings.py`:

```py
# пример в settings.py
from environ import Env
env = Env()
Env.read_env()  # loads .env
SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
DATABASES = {'default': env.db('DATABASE_URL')}
```

3) Пример GitHub Actions (создать `.github/workflows/ci.yml`):

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: python -m pip install --upgrade pip
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-django
      - run: pytest -q
```

4) Добавить `docker-compose.yml` для локальной разработки (web + db + nginx).

---

Если хотите, могу автоматически:

- создать `ANALYSIS.md` (сделал),
- добавить пример `.github/workflows/ci.yml`,
- сгенерировать `docker-compose.yml` и `requirements-dev.txt`,
- вынести секреты в `crm_local/settings.py` через `django-environ` и добавить `.env.example`.

Напишите, какие из этих действий выполнять автоматически. 
