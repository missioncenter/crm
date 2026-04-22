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
- `crm_local/` — основной Django проект
- `projects/` — приложение бизнес-логики
- `projects/static/` — CSS/JS, включая SortableJS для Kanban
- `projects/templates/` — шаблоны страниц
- `media/` — директория для загруженных файлов

## Важные файлы

- `crm_local/settings.py`
- `crm_local/urls.py`
- `supervisord.conf`
- `nginx.conf`
- `Dockerfile`
- `projects/models.py`
- `projects/views.py`
- `projects/forms.py`
- `projects/admin.py`

## Локальный запуск на Windows 11

1. Откройте PowerShell в папке проекта.
2. Создайте виртуальное среду:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Установите зависимости:

```powershell
pip install -r requirements.txt
```

4. Выполните миграции:

```powershell
python manage.py migrate
```

5. Создайте суперпользователя:

```powershell
python manage.py createsuperuser
```

6. Запустите сервер:

```powershell
python manage.py runserver 9090
```

7. Откройте в браузере:

- `http://127.0.0.1:9090/`
- `http://127.0.0.1:9090/projects/`
- `http://127.0.0.1:9090/tasks/`
- `http://127.0.0.1:9090/users/`
- `http://127.0.0.1:9090/groups/`
- `http://127.0.0.1:9090/calendar/`
- `http://127.0.0.1:9090/accounts/login/`

## Docker-сборка и запуск

Соберите образ:

```powershell
docker build -t crm-local-mvp .
```

Запустите контейнер с томами для базы и медиа:

```powershell
docker run -d --name crm-local-mvp \
  -p 9090:9090 \
  -v "%cd%\db.sqlite3:/app/db.sqlite3" \
  -v "%cd%\media:/app/media" \
  crm-local-mvp
```

> В PowerShell можно также использовать `${PWD}` вместо `%cd%`.

## Настройка статики

В `Dockerfile` выполняется:

```dockerfile
RUN python manage.py collectstatic --noinput
```

После этого `nginx` обслуживает статику из `/app/staticfiles`.

## Маршруты и страницы

- `/` — дашборд Kanban + статистика
- `/projects/` — список проектов
- `/projects/create/` — создание проекта
- `/projects/<id>/edit/` — редактирование проекта
- `/projects/<id>/delete/` — удаление проекта
- `/tasks/` — список задач
- `/tasks/create/` — создание задачи
- `/tasks/<id>/edit/` — редактирование задачи
- `/tasks/<id>/delete/` — удаление задачи
- `/calendar/` — календарный просмотр задач
- `/users/` — список пользователей
- `/users/create/` — создание пользователя
- `/users/<id>/edit/` — редактирование пользователя
- `/users/<id>/delete/` — удаление пользователя
- `/groups/` — список групп
- `/groups/create/` — создание группы
- `/groups/<id>/edit/` — редактирование группы
- `/groups/<id>/delete/` — удаление группы
- `/accounts/login/` — вход
- `/accounts/logout/` — выход

## Роли и права

- `Admins` и `staff`:
  - управляют проектами, задачами, группами и пользователями
- Исполнители и со-исполнители:
  - могут менять статус задач
- `Project.owner` и участники проекта:
  - могут видеть задачи и участвовать в работе
- `overdue` задачи помечаются автоматически, если дедлайн прошёл, а статус не `Done`

## Что ещё можно сделать

- добавить поиск и фильтрацию задач по проекту, исполнителю и статусу
- вынести страницу логина в отдельный шаблон `registration/login.html` с кастомным дизайном
- добавить загрузку файлов для задач и проектов
- подключить внешнюю базу данных PostgreSQL для продакшн-развёртывания
- добавить Docker Compose для удобного локального развёртывания
