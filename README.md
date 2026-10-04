# Разработка и интеграция — Учебная доставка

Один [репозиторий дисциплины](https://github.com/Kirill-Erofeev/development-and-integration-labs) содержит код проекта в корне,
условия и материалы по папкам семинаров. Этот этап развивает существующий
классификатор Iris; ветка этапа — `course/lab-08-delivery`.
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

## HTTP API

```powershell
py -3.11 -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

Модель загружается один раз при старте процесса. `ML_MODEL_PATH` задаёт путь к
доверенному артефакту; по умолчанию используется `models/model.pkl`.
Отсутствующая или повреждённая модель приводит к ошибке старта.
Swagger UI запущенного API: <http://127.0.0.1:8000/docs>.

| Операция | Контракт |
| --- | --- |
| `GET /health` | `{"status":"ok","model_ready":true}` при готовой модели |
| `POST /predict` | Четыре положительных конечных числа; ответ `prediction`, `class_name` |
| `GET /openapi.json` | Схема текущего приложения |

В другом терминале:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health | ConvertTo-Json
$body = '{"sepal_length":5.1,"sepal_width":3.5,"petal_length":1.4,"petal_width":0.2}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/predict -ContentType application/json -Body $body | ConvertTo-Json
```

Для этого контрольного примера ожидается `{"prediction":0,"class_name":"setosa"}`.
Пропуски, лишние поля, строки вместо чисел, `NaN`, бесконечности и неположительные
значения приводят к `422`. Если модель не готова во время обработки, `/predict`
возвращает `503`. Остановка локального сервера — `Ctrl+C`.

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

## Статус проверок

Для этого этапа ещё требуется зафиксировать фактический прогон и снимки.
Протокол: [Семинар 25.09.2026/CHECKS.md](<Семинар 25.09.2026/CHECKS.md>).
Сценарий и перечень снимков: [PRACTICE_8.md](<Семинар 25.09.2026/PRACTICE_8.md>).
До заполнения протокола команды и ожидаемые ответы не являются утверждением об успешном запуске.
Новые ссылки на PR, Actions и Pages добавляются по результату реальных действий.
