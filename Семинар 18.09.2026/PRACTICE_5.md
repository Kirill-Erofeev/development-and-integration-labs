# Практика 5 — контейнер API

## Требование и реализация

`Dockerfile` использует Python 3.11 slim, устанавливает закреплённые зависимости
и копирует только код API, общий сервис и сохранённый `models/model.pkl`.
`.dockerignore` ограничивает контекст необходимыми файлами. Обучение при сборке
и старте не выполняется. Один worker Uvicorn слушает `0.0.0.0:8000` внутри контейнера.

## Сборка и первая проверка

```powershell
docker build --file Dockerfile --tag ml-api:practice5 .
docker run -d --name ml-api-practice5 --cpus 1 --memory 512m -p 127.0.0.1:8080:8000 ml-api:practice5
docker ps --filter name=ml-api-practice5
docker logs ml-api-practice5
py -3.11 scripts/check_api.py --base-url http://127.0.0.1:8080
```

Дождитесь завершения startup перед smoke-проверкой. `check_api.py` выполняет
реальные `/health` и `/predict` с таймаутом и сверяет `model_ready: true`,
`prediction: 0`, `class_name: "setosa"`; ошибка возвращает код `1`.
Порт опубликован только на loopback хоста. Swagger UI доступен на
`http://127.0.0.1:8080/docs`.

## Повторный запуск того же образа

Следующие команды относятся только к созданному выше контейнеру:

```powershell
docker stop ml-api-practice5
docker rm ml-api-practice5
docker run -d --name ml-api-practice5 --cpus 1 --memory 512m -p 127.0.0.1:8080:8000 ml-api:practice5
docker logs ml-api-practice5
py -3.11 scripts/check_api.py --base-url http://127.0.0.1:8080
```

Сборка повторно не нужна. После готовности модель должна давать прежний ответ.
Зафиксируйте image ID, состояние контейнера, startup и HTTP-проверку; успешный
`docker build` отдельно не доказывает работу контейнера.
По окончании остановите и удалите только `ml-api-practice5`, чтобы освободить порт `8080`.

## Проверки и материалы сдачи

Статус: **фактический прогон выполнен; результаты и проверенный SHA приведены в CHECKS.md**. Команды и ожидаемые результаты
выше являются проверочным сценарием, а не протоколом уже выполненной проверки.
Фактические команды, коды завершения, версия Python, проверенный commit, результаты
и ссылки на новые PR/runs добавляются в [CHECKS.md](CHECKS.md).

Планируемые снимки после успешных проверок:

- [practice5-build.png](screenshots/practice5-build.png).
- [practice5-runtime.png](screenshots/practice5-runtime.png).
- [practice5-repeat.png](screenshots/practice5-repeat.png).

Ссылка считается подтверждением только после добавления соответствующего файла.
Снимки фиксируют проверенный коммит; последующее добавление материалов сдачи
не должно подменять его другим состоянием кода. Старые прогоны не подтверждают этот этап.
Word-отчёт оформляется пользователем отдельно после получения снимков.
