# CRM Local MVP

Проект представляет собой минимальный проектный менеджер на Django с Kanban-доской, CRUD для проектов, задач, пользователей и групп, а также Single-Container инфраструктурой на Docker.

## Обзор

CRM Local MVP построен как минимальный аналог Bitrix24:

- Django + SQLite
- Nginx + Gunicorn, управляемые supervisord
- Статическая сборка через `collectstatic`
- Kanban-интерфейс с drag-and-drop и AJAX-обновлением
- Пользователи, группы, проекты, задачи и календарь

## Что реализовано

- `Project`:
  - `title`, `description`
  - `owner`, `members`
- `Task`:
  - `title`, `description`, `status`, `deadline`
  - `project`, `executor`, `co_executors`
- `Calendar`:
  - просмотр задач по дедлайнам
  - отдельная секция для задач без дедлайна
- Роли и права:
  - `Admins` и `staff` могут управлять проектами, задачами и группами
  - исполнители и со-исполнители могут менять статус задач
  - `overdue` пометки для просроченных задач
- UI:
  - главная Kanban-доска
  - статистика на дашборде: проекты, группы, пользователи, задачи, просроченные
  - Material-подобный дизайн
  - логин-страница без шапки и меню
- CRUD:
  - `Projects`, `Tasks`, `Users`, `Groups`
- Аутентификация:
  - вход через `/accounts/login/`
  - выход через `/accounts/logout/` с редиректом на логин

## Структура проекта

- `Dockerfile` — образ на `python:3.12-slim`
- `supervisord.conf` — управление `gunicorn` и `nginx`
- `nginx.conf` — проксирование на порт `8000` и выдача `static`/`media`
- `manage.py` — Django CLI
- `core/` — основной Django проект
- `projects/` — приложение бизнес-логики
- `projects/static/` — CSS/JS, включая SortableJS для Kanban
- `projects/templates/` — шаблоны страниц
- `media/` — директория для загруженных файлов

## Важные файлы

- `core/settings.py`
- `core/urls.py`
- `supervisord.conf`
- `nginx.conf`
- `Dockerfile`
- `projects/models.py`
- `projects/views.py`
- `projects/forms.py`
- `projects/admin.py`

## Локальный запуск на Windows 11

# CRM Local — Copilot instructions

Кратко: проект — минимальный проектный менеджер на Django (app: `projects`).

Что изменено недавно:
- Добавлен `.gitignore`.
- Обновлён `README.md` с кратким обзором.
- Добавлен `docs/analysis.md` с глубоким анализом и рекомендациями.

Советы для Copilot (коротко):
- При изменениях конфигурации рекомендовать вынос секретов в переменные окружения и использование `.env.example`.
- Для изменений Docker/CI предлагать `docker-compose.yml` и пример `.github/workflows/ci.yml`.
- Для изменений кода — предлагать тесты (pytest-django) и pre-commit hooks.

Полезные места в репозитории:
- `core/settings.py` — настройки проекта
- `projects/models.py`, `projects/views.py`, `projects/forms.py` — основная логика
- `Dockerfile`, `supervisord.conf`, `nginx.conf` — контейнер/сервер

Если нужно, могу автоматически добавить:
- `docker-compose.yml` (web + postgres + nginx),
- `.github/workflows/ci.yml` (тесты + lint),
- `.env.example` и изменения в `settings.py` для загрузки из окружения.

Оставьте пожелания — выполню автоматически.

