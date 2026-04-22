# CRM Local MVP

Проект представляет собой минимальный проектный менеджер на Django с Kanban-доской и Single-Container инфраструктурой.

## Структура

- `Dockerfile` — позволяет собрать контейнер на `python:3.12-slim`
- `supervisord.conf` — запуск `gunicorn` + `nginx`
- `nginx.conf` — проксирование на `gunicorn` и выдача `static`/`media`
- `crm_local/` — Django проект
- `projects/` — приложение с моделями, канбан-дашбордом и AJAX-обновлением статуса

## Запуск локально на Windows 11

1. Откройте PowerShell в папке проекта.
2. Создайте виртуальное окружение:

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

6. Запустите проект локально (для разработки):

```powershell
python manage.py runserver
```

## Сборка Docker-контейнера

Соберите образ:

```powershell
docker build -t crm-local-mvp .
```

Запустите контейнер с монтированием базы и медиа:

```powershell
docker run -d --name crm-local-mvp \
  -p 9090:9090 \
  -v "%cd%\db.sqlite3:/app/db.sqlite3" \
  -v "%cd%\media:/app/media" \
  crm-local-mvp
```

> В PowerShell можно также использовать `${PWD}` вместо `%cd%`.

## Сборка и collectstatic

В `Dockerfile` выполняется:

```dockerfile
RUN python manage.py collectstatic --noinput
```

Это собирает статику в `/app/staticfiles`, которую затем обслуживает `nginx`.

## Примечания по роли и правам

- `Admins` и `staff` могут управлять проектами и менять статусы
- `executor` и `co-executor` могут перемещать задачи по статусам
- Задача помечается `overdue`, если дедлайн прошел и задача не в статусе `Done`
