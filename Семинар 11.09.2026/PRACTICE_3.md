# Практика 3 — HTTP API модели

## Требование и реализация

`app/api.py` экспортирует объект FastAPI `app`; схемы запроса/ответа находятся
в `app/schemas.py`. Общий `ModelService` в `src/model_service.py` загружает
сохранённый артефакт и используется CLI и API. Загрузка выполняется в lifespan
один раз на процесс; импорт модуля не запускает Uvicorn и не обучает модель.

## Запуск и контракт

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

## Отрицательный запрос

При работающем сервере выполните в другом PowerShell:

```powershell
$invalidBody = '{"sepal_length":5.1,"sepal_width":3.5,"petal_length":1.4,"petal_width":0}'
try {
    Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/predict -ContentType application/json -Body $invalidBody
} catch {
    [int]$_.Exception.Response.StatusCode
    $_.ErrorDetails.Message
}
```

Ожидаются статус `422` и описание ошибки `petal_width`. Некорректные `NaN` и
бесконечности не должны попадать в JSON ответа как невалидные числовые значения.
На снимке Swagger UI раскройте `/predict`: должны быть видны четыре признака,
схема ответа и код `422`. `/health` проверяется отдельным HTTP-запросом.

## Проверки и материалы сдачи

Статус: **ожидает прогона для коммита этого этапа**. Команды и ожидаемые результаты
выше являются проверочным сценарием, а не протоколом уже выполненной проверки.
Фактические команды, коды завершения, версия Python, проверенный commit, результаты
и ссылки на новые PR/runs добавляются в [CHECKS.md](CHECKS.md).

Планируемые снимки после успешных проверок:

- [practice3-startup.png](screenshots/practice3-startup.png).
- [practice3-health.png](screenshots/practice3-health.png).
- [practice3-predict.png](screenshots/practice3-predict.png).
- [practice3-docs.png](screenshots/practice3-docs.png).

Ссылка считается подтверждением только после добавления соответствующего файла.
Снимки фиксируют проверенный коммит; последующее добавление материалов сдачи
не должно подменять его другим состоянием кода. Старые прогоны не подтверждают этот этап.
Word-отчёт оформляется пользователем отдельно после получения снимков.
