# Практическая работа 6. Интеграция через Docker Compose

29 сентября 2026 года стенд проверен реальным запуском: API `healthy`, клиент
завершился с кодом `0`, результат сохранён на хосте. Проверены ошибочный
адрес `localhost`, исправление и сохранность файла после остановки.
Команды выполняются из корня репозитория.

## Компоненты и адреса

| Компонент | Настройка | Назначение |
| --- | --- | --- |
| `api` | Контекст `.`, образ `ml-api:practice6` | API практики 5 с готовой моделью |
| `api` | `ML_MODEL_PATH=/app/models/model.pkl` | Согласованное существующее имя переменной |
| `api` | `127.0.0.1:8080:8000` | Доступ с хоста по `http://127.0.0.1:8080` |
| `client` | Контекст `./client`, образ `ml-client:practice6` | Отдельный одноразовый процесс |
| `client` | `API_URL=http://api:8000` | Адрес API внутри общей сети `app_net` |
| `client` | `RESULT_PATH=/results/prediction.json` | Файл ответа внутри контейнера |
| Bind mount | `./results:/results` | Сохранение ответа в папке проекта на хосте |

Схема взаимодействия приведена в [README](README.md). В сети Compose имя `api`
разрешается как имя сервиса; обращения между сервисами используют порт `8000`
контейнера. Опубликованный порт `8080` нужен клиенту на хосте. `localhost` внутри
контейнера обозначает этот же контейнер.
Сверено 19.09.2026 с [описанием сети Compose](https://docs.docker.com/compose/how-tos/networking/).

Healthcheck API проверяет `/health`, `status == "ok"` и `model_ready == true`.
Условие `depends_on: service_healthy` откладывает старт клиента до успешной проверки.
Это проверка готовности к старту клиента, а не гарантия доступности на всё время работы.
Сверено 19.09.2026 с [порядком запуска Compose](https://docs.docker.com/compose/how-tos/startup-order/).

Клиент отправляет один синтетический запрос `/predict` с `timeout=10`, вызывает
`raise_for_status` и проверяет JSON-объект с ровно двумя полями: `prediction` — целое
число `0`, `1` или `2` (логическое значение не принимается), `class_name` —
соответственно `setosa`, `versicolor` или `virginica`. Только проверенный ответ
записывается в файл. Ошибка завершает процесс с кодом `1` и сохраняет прежний результат.
Успешный одноразовый клиент завершается с кодом `0`; постоянный процесс ему не нужен.

API ограничен `1 CPU / 512 MiB`, клиент — `0.25 CPU / 128 MiB`.
Лимиты относятся к контейнерам при выполнении; они не ограничивают всю VM Docker
Desktop/WSL и расход ресурсов сборки. `--parallel 1` последовательно выполняет
операции Compose, включая сборку образов.
Сверено 19.09.2026 с [параметрами Compose](https://docs.docker.com/reference/cli/docker/compose/).

## Запуск и проверка

Все команды выполняются в PowerShell из корня репозитория. Из папки материалов
перейдите туда командой ниже; если терминал уже в корне, пропустите `Set-Location`. Контейнер `ml-api-practice5-20260929` из практики 5 должен быть остановлен,
чтобы освободить порт `8080`.

```powershell
Set-Location -LiteralPath '..'
docker compose -p course-labs-20260929 config
if ($LASTEXITCODE -ne 0) { throw 'Compose configuration is invalid' }
docker compose -p course-labs-20260929 --parallel 1 build api
if ($LASTEXITCODE -ne 0) { throw 'API image build failed' }
docker compose -p course-labs-20260929 --parallel 1 build client
if ($LASTEXITCODE -ne 0) { throw 'Client image build failed' }
docker compose -p course-labs-20260929 --parallel 1 up --no-build -d
if ($LASTEXITCODE -ne 0) { throw 'Compose startup failed' }
docker compose -p course-labs-20260929 ps -a
docker compose -p course-labs-20260929 logs api client
Invoke-RestMethod -Uri http://127.0.0.1:8080/health -TimeoutSec 10 | ConvertTo-Json
```

`config` должен показать корректные контексты сборки, переменные, порт, сеть и bind
mount. После завершения запроса ожидаются `api` со статусом `healthy` и `client`
со статусом `Exited (0)`. Если клиент ещё работает, дождитесь его завершения и
повторите `ps -a` и просмотр логов.

Проверьте код завершения клиента и файл:

```powershell
$clientContainer = docker compose -p course-labs-20260929 ps -a -q client
if (-not $clientContainer) { throw 'Client container was not found' }
docker inspect --format '{{.State.ExitCode}}' $clientContainer
Get-Item -LiteralPath '.\results\prediction.json' | Select-Object FullName, LastWriteTime
Get-Content -LiteralPath '.\results\prediction.json' -Encoding UTF8
```

Ожидаемый ответ для синтетического примера —
`{"prediction":0,"class_name":"setosa"}`. Файл сам по себе не доказывает успех
текущего запуска: он мог остаться от предыдущего. Сопоставьте статус `Exited (0)`,
код завершения, логи текущего запуска с `http://api:8000` и время изменения файла.
Такой JSON получен в успешном прогоне 29.09.2026.

## Ошибка адреса и исправление

При работающем API запустите отдельный клиент с ошибочным адресом:

```powershell
docker compose -p course-labs-20260929 run --rm -e API_URL=http://localhost:8000 client
$wrongUrlExitCode = $LASTEXITCODE
Write-Output "Wrong URL exit code: $wrongUrlExitCode"
if ($wrongUrlExitCode -eq 0) { throw 'Expected a connection failure' }
```

Внутри `client` нет API на порту `8000`, поэтому ожидаются сообщение об ошибке и
ненулевой код. Старый `results/prediction.json` должен сохраниться; его наличие
не означает, что ошибочный запрос прошёл. Вывод `run --rm` фиксируется в текущем
терминале: после завершения этот отдельный контейнер удаляется.

Повторите запуск с адресом из `compose.yaml`:

```powershell
docker compose -p course-labs-20260929 run --rm client
$correctUrlExitCode = $LASTEXITCODE
Write-Output "Correct URL exit code: $correctUrlExitCode"
if ($correctUrlExitCode -ne 0) { throw 'Corrected client run failed' }
Get-Content -LiteralPath '.\results\prediction.json' -Encoding UTF8
```

Для исправленного запуска ожидаются код `0`, вывод о сохранении проверенного
ответа и актуальный JSON. `docker compose -p course-labs-20260929 logs client` относится к сервисному
контейнеру первого запуска и не заменяет вывод этих одноразовых `run --rm`.

## Остановка и сохранность результата

```powershell
docker compose -p course-labs-20260929 down
if ($LASTEXITCODE -ne 0) { throw 'Compose shutdown failed' }
Get-Content -LiteralPath '.\results\prediction.json' -Encoding UTF8
```

Ожидается, что контейнеры и сеть этого Compose-проекта удалены, а файл в `./results`
остаётся на хосте благодаря bind mount. `results/.gitkeep` сохраняет пустой каталог
в репозитории до первого запуска. Файл `prediction.json`
не добавлен в `.gitignore`; после запуска он будет виден в Git-статусе.

## Что объяснить и зафиксировать

Dockerfile описывает один образ, Compose — конфигурацию и взаимодействие сервисов.
Разные контексты и Dockerfile позволяют API и клиенту устанавливать собственные
зависимости и выполнять разные команды. `image` задаёт имя результата сборки;
при наличии `build` его можно не задавать явно. Healthcheck проверяет готовность,
а `depends_on` использует результат для порядка запуска. Левая часть bind mount
относится к хосту, правая — к контейнеру. `Exited (0)` означает успешное завершение
одноразового клиента.

## Выполненные проверки, 29.09.2026

| Проверка | Фактический результат |
| --- | --- |
| `compose config` и сборки обоих сервисов | Код `0` |
| Состояние API | `healthy` |
| Состояние клиента | `exited`, код `0` |
| Общая сеть | `app_net`, драйвер `bridge` |
| Лимиты | API: 1 CPU / 512 MiB; клиент: 0.25 CPU / 128 MiB |
| Первый результат | `{"prediction":0,"class_name":"setosa"}`, проверено свежее время записи |
| `API_URL=http://localhost:8000` | Код `1`; содержимое и время записи прежнего файла не изменились |
| Повтор с `http://api:8000` | Код `0`, свежий результат |
| `down` | Код `0`; файл сохранился без изменения содержимого |

[Состояние стенда](screenshots/practice6-status.png),
[ошибка и исправление](screenshots/practice6-localhost.png),
[сохранность после down](screenshots/practice6-persistence.png).
Полный протокол — [CHECKS.md](CHECKS.md). Проверка чистого клона:
[отчёт чистого клона и CI/CD](<../Семинар 25.09.2026/CHECKS.md>); её результат фиксируется отдельно.
