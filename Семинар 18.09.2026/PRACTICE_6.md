# Практика 6 — Docker Compose

## Требование и реализация

`compose.yaml` связывает API и отдельный Python-клиент сетью `app_net`.
`api` становится healthy после успешного `/health`; `client` зависит от этого
состояния, отправляет один контрольный запрос и сохраняет проверенный ответ
в `/results/prediction.json`. Bind mount связывает `/results` с `./results` хоста.

## Запуск и сохранность результата

```powershell
docker compose up --build -d
docker compose ps -a
docker compose logs api client
py -3.11 scripts/check_api.py --base-url http://127.0.0.1:8080
```

API доступен на `http://127.0.0.1:8080`; внутри сети клиент обращается к
`http://api:8000`. Сервис `client` выполняет один запрос и успешно завершается с
кодом `0`, а `api` продолжает работу. Результат сохраняется в обычный JSON
`results/prediction.json` через bind mount. `localhost` внутри клиента указывает
на сам контейнер клиента и не заменяет имя сервиса `api`.

```powershell
Get-Content -Encoding UTF8 results/prediction.json
docker compose down
Get-Content -Encoding UTF8 results/prediction.json
```

`down` удаляет контейнеры и сеть этого Compose-проекта; сохранённый файл результата
остаётся в каталоге проекта. Для полного набора тестов клиента дополнительно
установите `py -3.11 -m pip install -r client/requirements.txt`.

## Отрицательный пример с localhost

При работающем healthy API запустите отдельный одноразовый клиент с неверным адресом:

```powershell
docker compose run --rm --no-deps -e API_URL=http://127.0.0.1:8000 client
```

Ожидается ошибка соединения и ненулевой код завершения: loopback относится к
контейнеру клиента. Предыдущий `results/prediction.json` не должен измениться,
поскольку запись выполняется только после успешного запроса и проверки ответа.
Затем обычный клиент должен снова успешно обращаться к `http://api:8000`.

В CHECKS.md сравните JSON до ошибочного запуска, после него и после `docker compose down`.
Также запишите exit code клиента и состояние API. `client: Exited (0)` здесь
является ожидаемым успешным завершением одноразовой работы.

## Проверки и материалы сдачи

Статус: **ожидает прогона для коммита этого этапа**. Команды и ожидаемые результаты
выше являются проверочным сценарием, а не протоколом уже выполненной проверки.
Фактические команды, коды завершения, версия Python, проверенный commit, результаты
и ссылки на новые PR/runs добавляются в [CHECKS.md](CHECKS.md).

Планируемые снимки после успешных проверок:

- [practice6-status.png](screenshots/practice6-status.png).
- [practice6-localhost.png](screenshots/practice6-localhost.png).
- [practice6-persistence.png](screenshots/practice6-persistence.png).

Ссылка считается подтверждением только после добавления соответствующего файла.
Снимки фиксируют проверенный коммит; последующее добавление материалов сдачи
не должно подменять его другим состоянием кода. Старые прогоны не подтверждают этот этап.
Word-отчёт оформляется пользователем отдельно после получения снимков.
