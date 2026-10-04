# Разработка и интеграция — Зачёт: вариант 4

Один [репозиторий дисциплины](https://github.com/Kirill-Erofeev/development-and-integration-labs) содержит код проекта в корне,
условия и материалы по папкам семинаров. Этот этап развивает существующий
классификатор Iris; ветка этапа — `course/exam-4`.
GitHub используется по решению владельца: pull request, Actions и Pages заменяют
соответствующие механизмы GitVerse из учебных материалов.

Вывод CLI: JSON используется по умолчанию, --output-format text включает текст; диагностика поступает в stderr.

## Работы к этому этапу

- [Структура ML-проекта](<Семинар 04.09.2026/PRACTICE_1.md>).
- [Git и коллективная разработка](<Семинар 11.09.2026/PRACTICE_2.md>).
- [HTTP API модели](<Семинар 11.09.2026/PRACTICE_3.md>).
- [Модульные и интеграционные тесты](<Семинар 11.09.2026/PRACTICE_4.md>).
- [Контейнер API](<Семинар 18.09.2026/PRACTICE_5.md>).
- [Docker Compose](<Семинар 18.09.2026/PRACTICE_6.md>).
- [GitHub Actions CI](<Семинар 25.09.2026/PRACTICE_7.md>).
- [Учебная доставка](<Семинар 25.09.2026/PRACTICE_8.md>).
- [Swagger UI и Pages](<Семинар 02.10.2026/PRACTICE_9.md>).
- [Зачёт: вариант 4](<Зачёт 09.10.2026/PRACTICE_4.md>).

Лекции и организационные материалы сохранены в своих исходных папках.
Word-отчёты пользователь оформляет отдельно; они не подменяются этим README.

## Среда и CLI

Все команды выполняются из корня репозитория в PowerShell. Используется глобальный
Python 3.11; отдельное виртуальное окружение не требуется. Версии Python-пакетов
закреплены в `requirements.txt`. На Linux вместо `py -3.11` используется `python3.11`.

```powershell
py -3.11 -m pip install -r requirements.txt
py -3.11 src/predict.py
py -3.11 -m pytest -q
```

CLI принимает `--input` и `--model-path`; значения по умолчанию —
`data_sample/sample.csv` и `models/model.pkl`. Он возвращает список объектов
с полями `predicted_class` и `predicted_name`. Ошибки входа или модели завершают
команду кодом `2`. Стандартные пути вычисляются относительно проекта;
явно переданные относительные пути — относительно текущего каталога.

Для отдельной проверки обучения без замены сохранённой модели проекта:

```powershell
py -3.11 src/train.py --model-path .verification/training/model.pkl
py -3.11 src/predict.py --model-path .verification/training/model.pkl
```

Обучение сохраняет словарь с моделью, порядком признаков и именами классов.
Предсказание использует готовый артефакт и не вызывает `fit`.

Текстовый вывод включается отдельно:

```powershell
py -3.11 src/predict.py --output-format text
```

Для контрольного примера ожидается строка `predicted_class=0 predicted_name=setosa`.
Выбор формата не изменяет порядок объектов и вычисление прогноза.

## Действующий API варианта 4

Модель и CLI сохранены. HTTP-контракт изменён: `prediction` заменено на `class_id`,
`model_ready` — на `model_loaded`. Новый `request_id` связывает запрос, ответ и лог.
Клиент, smoke-проверка, healthcheck Compose и OpenAPI согласованы с этим контрактом.

```powershell
py -3.11 -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

Веб-страница: <http://127.0.0.1:8000/>; Swagger UI: <http://127.0.0.1:8000/docs>.
Модель загружается в lifespan; `ML_MODEL_PATH` позволяет выбрать доверенный артефакт.
При ошибке его загрузки запуск останавливается.

| Операция | Успешный ответ |
| --- | --- |
| `GET /` | HTML-страница с паспортом модели и формой |
| `GET /health` | `{"status":"ok","model_loaded":true}` |
| `GET /model-info` | `model_type`, `classes`, `feature_count`, `model_loaded` |
| `POST /predict` | `class_id`, `class_name`, `request_id`; заголовок `X-Request-ID` |
| `GET /openapi.json` | Схема нового контракта |

В другом терминале:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/model-info | ConvertTo-Json
$headers = @{ 'X-Request-ID' = 'e21f05a0-837f-4ea9-84a0-621ce8f8b0a8' }
$body = '{"sepal_length":5.1,"sepal_width":3.5,"petal_length":1.4,"petal_width":0.2}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/predict -Headers $headers -ContentType application/json -Body $body | ConvertTo-Json
py -3.11 scripts/check_api.py --base-url http://127.0.0.1:8000
```

Ожидаются `class_id: 0`, `class_name: "setosa"` и отправленный UUID.
Корректный UUID канонизируется; отсутствующий, пустой или неверный заголовок
заменяется новым UUIDv4. Для `/predict` идентификатор назначается до валидации:
он возвращается также в предусмотренных ответах с ошибками и в `X-Request-ID`.
Тело запроса требует четыре положительных конечных числа без лишних полей.
Ошибки полей или синтаксиса JSON дают `422`, некорректная кодировка тела — `400`,
неготовая модель — `503`, ошибка прогноза — безопасный `500`.

Паспорт раскрывает только `LogisticRegression`, имена трёх классов,
число признаков `4` и готовность. Пути, содержимое pickle и обучающие строки
не возвращаются. В журнал пишется `prediction_completed` с UUID и именем класса;
ошибки дают `prediction_rejected` или `prediction_failed` с UUID и HTTP-статусом.
Исходные признаки и некорректный заголовок не записываются.

## Контейнеры

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

## Автоматические проверки

[CI](.github/workflows/ci.yaml) запускается при pull request, push в `main` и
`workflow_dispatch`. Job `check` устанавливает Python 3.11 и оба requirements,
проверяет синтаксис и запускает полный pytest. После её успеха `build-image`
собирает два образа — API и клиента — с тегом `test-<SHA>`.
Собранные образы остаются на временном runner; workflow не отправляет их в registry.
Статус конкретного запуска подтверждается новой ссылкой в протоколе этапа.

## Учебная доставка

[Delivery Dry Run](.github/workflows/delivery.yaml) запускается вручную:
**Actions → Delivery Dry Run → Run workflow**. На `main` выполняется полный
сценарий из четырёх jobs. Для другой ветки `deploy_dry_run` получает `skipped`.

`build` формирует `test-<SHA>`. После неё параллельно выполняются
`smoke_api_tests_stub` и `docs_checks`; `deploy_dry_run` ожидает их успеха.
Команды pull/stop/rm/run, HTTP-проверки и rollback к `previous-stable` выводятся
в журнал. Это предусмотренная заданием имитация: workflow не запускает эти
команды, не публикует образ и не обращается к рабочему серверу.

## Статическая документация API

[Publish API documentation](.github/workflows/publish-api-docs.yaml) импортирует
`app.api:app` и вызывает `app.openapi()` через экспортёр без запуска API и модели.
Схема создаётся во временном каталоге CI; в Git остаются исходные страницы,
локальные CSS/JS Swagger UI и лицензии. CDN не используется.

```powershell
py -3.11 -m pytest -q scripts/tests/test_export_openapi.py
py -3.11 -m scripts.build_api_docs --output site
py -3.11 -m http.server 8090 --bind 127.0.0.1 --directory site
```

Локальная страница: <http://127.0.0.1:8090/api/>. `site/` исключён из Git.
Для GitHub Pages выбирается источник **GitHub Actions**. Сборка выполняется при
PR, push в `main` и ручном запуске; публикация разрешена только на `main`.
Ручной запуск: **Actions → Publish API documentation → Run workflow → main**.

Опубликованные адреса документации:
[Swagger UI](https://kirill-erofeev.github.io/development-and-integration-labs/api/) и
[OpenAPI JSON](https://kirill-erofeev.github.io/development-and-integration-labs/api/openapi.json).
Pages не запускает Python: отправка запросов в статическом Swagger UI отключена.
Для работы с моделью используйте `/docs` запущенного API.

## Проверка зачёта

```powershell
py -3.11 -m pytest -q tests/test_variant4.py
py -3.11 -m pytest -q
docker compose up --build -d
docker compose logs api client
```

На странице проверьте паспорт, успешный прогноз с UUID и ошибку при `petal_width=0`.
Сопоставьте UUID браузера, JSON ответа и события в журнале API. Через Compose
страница открывается по `http://127.0.0.1:8080/`.
В `notebooks/variant4/` сохранены рабочие эксперименты, использующие общие модули
без переобучения модели. По согласованному исключению рецензирование выполняется
как учебный саморазбор автора в PR; независимое одобрение не заявляется.

## Статус проверок

Фактический прогон и снимки этого этапа зафиксированы в протоколе.
Протокол: [Зачёт 09.10.2026/CHECKS.md](<Зачёт 09.10.2026/CHECKS.md>).
Сценарий и перечень снимков: [PRACTICE_4.md](<Зачёт 09.10.2026/PRACTICE_4.md>).
Локальные проверки, контейнеры и новые GitHub Actions подтверждены журналами и ссылками в протоколах.

К защите: [ответы на 20 теоретических вопросов](<Зачёт 09.10.2026/THEORY.md>).

Материалы для Word-отчётов: [30 снимков в порядке вставки](СКРИНШОТЫ.md).
