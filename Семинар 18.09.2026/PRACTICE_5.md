# Практическая работа 5. Контейнеризация API

29 сентября 2026 года выполнены сборка и два запуска контейнера из одного образа.
Оба запуска подтвердили HTTP-контракты; диагностика и состав образа проверены.
Рабочий каталог команд — корень репозитория.

## Реализация

Базовый образ — `python:3.11-slim`; рабочий каталог контейнера — `/app`.
Зависимости из [requirements.txt](<../requirements.txt>) копируются
до кода, чтобы изменение приложения не отменяло кеш их установки. Установка
требует готовых бинарных пакетов и не запускает сборку Python-пакетов из исходников.
В образ входят только файлы API, его модуль работы с моделью и `models/model.pkl`.
Обучение при сборке и обработке HTTP-запроса отсутствует.

[app/api.py](<../app/api.py>) читает `ML_MODEL_PATH` и загружает
артефакт при старте. Имя переменной сохранено по согласованию с пользователем;
замена на `MODEL_PATH` из методички не требуется. API запускается одним worker,
Uvicorn слушает `0.0.0.0:8000`.

Контекст задаётся последней точкой в `docker build ... .`; пути `COPY` отсчитываются
от него. `.dockerignore` разрешает только необходимые файлы. Материалы семинаров
остаются в Git независимо от исключения из контекста сборки.
Правила контекста сверены 19.09.2026 с [документацией Docker](https://docs.docker.com/build/concepts/context/).

## Сборка и запуск

Откройте PowerShell в `Семинар 18.09.2026` и перейдите в корень репозитория.
Если терминал уже открыт в корне репозитория, переход не нужен.
Для проверки нужны запущенный Docker с Linux-контейнерами и свободный порт `8080`.

```powershell
Set-Location -LiteralPath '..'
docker version
docker build -t ml-api:practice5 .
if ($LASTEXITCODE -ne 0) { throw 'API image build failed' }
docker image ls ml-api
docker run -d --name ml-api-practice5-20260929 --cpus 1 --memory 512m `
    -p 127.0.0.1:8080:8000 -e ML_MODEL_PATH=/app/models/model.pkl ml-api:practice5
if ($LASTEXITCODE -ne 0) { throw 'API container start failed' }
```

Успешная сборка должна создать `ml-api:practice5`. Публикация связывает порт
`8080` локального хоста с портом `8000` контейнера. `EXPOSE 8000` в Dockerfile
документирует порт, а фактическую публикацию выполняет `-p`.
Лимиты `--cpus` и `--memory` относятся к этому работающему контейнеру, а не к
Docker Desktop/WSL целиком или предшествующей сборке.

## Проверка API и диагностика

После сообщения о готовности приложения в логах выполните:

```powershell
docker logs ml-api-practice5-20260929
Invoke-RestMethod -Uri http://127.0.0.1:8080/health -TimeoutSec 10 | ConvertTo-Json
$irisRequest = @{
    sepal_length = 5.1
    sepal_width = 3.5
    petal_length = 1.4
    petal_width = 0.2
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8080/predict `
    -ContentType 'application/json' -Body $irisRequest -TimeoutSec 10 | ConvertTo-Json
docker ps --filter name=ml-api-practice5-20260929
docker exec ml-api-practice5-20260929 pwd
docker exec ml-api-practice5-20260929 ls -la /app
docker stats --no-stream ml-api-practice5-20260929
```

Ожидаются успешные HTTP-ответы: `/health` возвращает
`{"status":"ok","model_ready":true}`, а `/predict` для приведённого примера —
`{"prediction":0,"class_name":"setosa"}`. Оба ответа подтверждены реальным запуском 29.09.2026. `pwd` должен вывести `/app`; в нём должны быть приложение,
runtime-модули и модель.

Дополнительная проверка обоих маршрутов одной командой после запуска API:

```powershell
py -3.11 scripts/check_api.py --base-url http://127.0.0.1:8080
```

Скрипт [check_api.py](<../scripts/check_api.py>) обращается к уже
работающему API; Docker и сервер самостоятельно не запускает.

## Повторный запуск

Следующие команды останавливают и удаляют только созданный выше `ml-api-practice5-20260929`.
После удаления создайте контейнер из того же образа:

```powershell
docker stop ml-api-practice5-20260929
docker rm ml-api-practice5-20260929
docker run -d --name ml-api-practice5-20260929 --cpus 1 --memory 512m `
    -p 127.0.0.1:8080:8000 -e ML_MODEL_PATH=/app/models/model.pkl ml-api:practice5
if ($LASTEXITCODE -ne 0) { throw 'API container restart failed' }
docker logs ml-api-practice5-20260929
```

Дождитесь готовности API и повторите запросы `/health` и `/predict` из предыдущего
раздела. Сопоставьте оба ответа с первым запуском. Затем освободите порт для практики 6:

```powershell
docker stop ml-api-practice5-20260929
docker rm ml-api-practice5-20260929
```

## Что объяснить и зафиксировать

`docker build` создаёт образ с файловой системой и настройками; `docker run`
создаёт и запускает контейнер из образа. `WORKDIR` задаёт каталог внутри образа,
`RUN` выполняется при сборке, `CMD` — при запуске. Адрес `0.0.0.0` позволяет
принимать запросы на сетевом интерфейсе контейнера. Логи доступны через `logs`,
диагностические команды внутри работающего контейнера — через `exec`.

## Выполненные проверки, 29.09.2026

| Проверка | Фактический результат |
| --- | --- |
| Сборка `ml-api:practice5` | Код `0`, 99.766 с |
| `/health` | HTTP `200`, `{"status":"ok","model_ready":true}` |
| `/predict` | HTTP `200`, `{"prediction":0,"class_name":"setosa"}` |
| Диагностика | `ps`, `logs`, `exec pwd`, `exec ls`, `stats --no-stream`: код `0` |
| Рабочий каталог | `/app` |
| Лимиты | 1 CPU / 512 MiB |
| Пересоздание | Повторные `/health` и `/predict` успешны; ответы совпали |
| Состав образа | Нужные runtime-файлы и модель существуют; исключённые пути отсутствуют |

[Сборка](screenshots/practice5-build.png),
[работа и диагностика](screenshots/practice5-runtime.png),
[повторный запуск](screenshots/practice5-repeat.png).
Полный протокол и список проверенных путей — [CHECKS.md](CHECKS.md).
Отдельная проверка воспроизводимости: [отчёт чистого клона и CI/CD](<../Семинар 25.09.2026/CHECKS.md>).

## Выполненные проверки, 19.09.2026

Девять тестовых сценариев `scripts/tests` прошли в общем прогоне 40 новых тестов
за 1,33 секунды. HTTP-ответы имитировались; сеть и модель не использовались.
Проверены существование путей `COPY`, список разрешённых файлов контекста,
синтаксис Python и зависимости по установленным метаданным для целевого Linux
с Python 3.11.
