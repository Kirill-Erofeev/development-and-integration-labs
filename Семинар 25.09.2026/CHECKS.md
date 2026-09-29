# Проверки чистого клона, Linux и учебной доставки

Дата: **29.09.2026**. Проверен опубликованный коммит
[`fdc377f`](https://github.com/Kirill-Erofeev/development-and-integration-labs/commit/fdc377f0d347f3ee1232871f07787daa4ad8b0e7) — `fdc377f0d347f3ee1232871f07787daa4ad8b0e7`,
ветка `feature/delivery-dry-run`. Полный прогон `fe895def76804e428344cc0ba511ccbf` имеет
статус `passed`: `2026-09-29T15:55:18.382+00:00` — `2026-09-29T15:56:50.903+00:00`.

## Чистый клон: Windows и локальный API

Фактический stdout полного pytest:

```text
........................................................................ [ 75%]
.......................                                                  [100%]
95 passed in 10.66s
```

Код завершения pytest — `0`.
Отдельный локальный Uvicorn подтвердил реальные `/health` и `/predict` с HTTP 200.

## Linux: версия, зависимости и полный pytest

Использован Linux-контейнер `ml-api:practice6` с клоном, подключённым только для чтения,
рабочим каталогом `/workspace` и `ML_MODEL_PATH=/workspace/models/model.pkl`.
В нём установлены зависимости клиента и выполнены `pip check` и полный pytest.

```text
Python: 3.11.16 (main, Sep 19 2026, 01:04:43) [GCC 14.2.0]
No broken requirements found.
........................................................................ [ 75%]
.......................                                                  [100%]
95 passed in 18.70s
```

Код контейнерного процесса — `0`. Его полная длительность,
включая установку зависимостей, составила **30.687 с**;
длительность самого pytest указана в его stdout выше. Полный вывод установки
и stderr сохранены в [CLONE_20260929.log](CLONE_20260929.log).

## Сборки и реальный Compose из клона

| Проверка | Фактический результат |
| --- | --- |
| API `ml-api:practice5` | Код `0`, 2.266 с |
| API Compose `ml-api:practice6` | Код `0`, 1.328 с |
| Клиент `ml-client:practice6` | Код `0`, 1.047 с |
| Config и up | Код 0 |
| API / клиент | `healthy` / `exited`, код клиента `0` |
| `/health` с хоста | HTTP 200, `{"status":"ok","model_ready":true}` |
| `/predict` и JSON клиента | HTTP 200, `{"prediction":0,"class_name":"setosa"}`; проверено свежее время записи |
| Ошибочный `http://localhost:8000` | Код `1`; содержимое и время записи прежнего файла сохранены |
| Исправленный `http://api:8000` | Код `0`; новый результат |
| Down | Код 0; контейнеры и сеть проекта удалены; JSON на хосте сохранился |

Команды и результаты взяты из успешного прогона клона.
Подробная проверка жизненного цикла P5 и снимки первого контейнерного прогона:
[практики 5–6](<../Семинар 18.09.2026/CHECKS.md>).

## Шесть локальных Bash-шагов delivery

Источник: workflow опубликованного `fdc377f`; тег
`test-fdc377f0d347f3ee1232871f07787daa4ad8b0e7`. Каждый блок исполнен локально в Bash с синтетическими
переменными GitHub. Проверены вывод тега, наличие README, предлагаемые запросы,
путь модели, обновление и откат. Docker и curl в этих блоках только печатаются.

| Шаг | Фактический код завершения |
| --- | --- |
| 1 | `0` |
| 2 | `0` |
| 3 | `0` |
| 4 | `0` |
| 5 | `0` |
| 6 | `0` |

Полный захваченный stdout шести шагов: [DELIVERY_20260929.log](DELIVERY_20260929.log).

## Опубликованные артефакты

- [CLONE_20260929.json](CLONE_20260929.json) — все статусы, параметры, HTTP-ответы и результаты клона.
- [CLONE_20260929.log](CLONE_20260929.log) — полные stdout/stderr команд, коды и длительности.
- [DELIVERY_20260929.log](DELIVERY_20260929.log) — stdout локальных печатающих Bash-шагов.
- [RUNTIME_20260929.json](<../Семинар 18.09.2026/RUNTIME_20260929.json>) и [RUNTIME_20260929.log](<../Семинар 18.09.2026/RUNTIME_20260929.log>) — исходный успешный контейнерный прогон.

JSON сохраняет исходное имя журнала `commands.log`; диапазоны stdout/stderr
относятся к соответствующему опубликованному файлу `CLONE_20260929.log` или `RUNTIME_20260929.log`.

## GitHub PR и Actions

Сохранённые подтверждения показывают слияние семи PR: [PR #1](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/1), [PR #2](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/2), [PR #3](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/3), [PR #4](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/4), [PR #5](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/5), [PR #6](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/6), [PR #7](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/7).
Merge commits и исходные SHA веток: [GITHUB.md](<../Семинар 11.09.2026/GITHUB.md>).

Метки времени runs и jobs получены из GitHub API; время формирования PNG —
из локальных часов Windows. Эти часы различаются на несколько минут.
Длительности jobs определяются по меткам GitHub; время в подписи PNG
не используется для сравнения с ними.

### CI на main

[CI #36596424256](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596424256); event `push`, ref `main`, SHA `8145a8252febca4b93b7580a40008f508aeb9e68`.
Run завершён `completed/success`; оба шага Docker-сборки и полный pytest успешны.

```text
95 passed in 5.13s
```

| Job | Статус | Начало | Завершение |
| --- | --- | --- | --- |
| `check` | `success` | `2026-09-29T16:15:50Z` | `2026-09-29T16:16:16Z` |
| `build-image` | `success` | `2026-09-29T16:16:21Z` | `2026-09-29T16:16:45Z` |

[Снимок CI](screenshots/practice7-ci.png), [CI_20260929.json](CI_20260929.json),
[CI_20260929.log](CI_20260929.log).

### Delivery на main

[Delivery main #36596835394](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596835394); event `workflow_dispatch`, ref `main`,
SHA `8145a8252febca4b93b7580a40008f508aeb9e68`. Тег `test-8145a8252febca4b93b7580a40008f508aeb9e68` передан в последующие
jobs; лог содержит предлагаемые Docker/HTTP-команды и откат к `previous-stable`.

| Job | Статус | Начало | Завершение |
| --- | --- | --- | --- |
| `build` | `success` | `2026-09-29T16:19:17Z` | `2026-09-29T16:19:20Z` |
| `docs_checks` | `success` | `2026-09-29T16:19:22Z` | `2026-09-29T16:19:26Z` |
| `smoke_api_tests_stub` | `success` | `2026-09-29T16:19:22Z` | `2026-09-29T16:19:25Z` |
| `deploy_dry_run` | `success` | `2026-09-29T16:19:29Z` | `2026-09-29T16:19:34Z` |

[Снимок main](screenshots/practice8-delivery.png),
[DELIVERY_MAIN_20260929.json](DELIVERY_MAIN_20260929.json),
[DELIVERY_MAIN_20260929.log](DELIVERY_MAIN_20260929.log).

### Ограничение ветки delivery

[Delivery feature #36596569372](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596569372); event `workflow_dispatch`, ref `feature/delivery-dry-run`,
SHA `fdc377f0d347f3ee1232871f07787daa4ad8b0e7`. Run завершён `success`; условие ветки пропустило
`deploy_dry_run`, три остальные jobs успешно завершены.

| Job | Статус | Начало | Завершение |
| --- | --- | --- | --- |
| `build` | `success` | `2026-09-29T16:17:04Z` | `2026-09-29T16:17:07Z` |
| `smoke_api_tests_stub` | `success` | `2026-09-29T16:17:10Z` | `2026-09-29T16:17:13Z` |
| `docs_checks` | `success` | `2026-09-29T16:17:11Z` | `2026-09-29T16:17:17Z` |
| `deploy_dry_run` | `skipped` | `2026-09-29T16:17:18Z` | `2026-09-29T16:17:17Z` |

[Снимок feature](screenshots/practice8-branch.png),
[DELIVERY_BRANCH_20260929.json](DELIVERY_BRANCH_20260929.json),
[DELIVERY_BRANCH_20260929.log](DELIVERY_BRANCH_20260929.log).
Delivery остаётся учебным dry run: Docker и HTTP-команды печатаются в лог.

## Итоговый клон main

После слияний проверен новый клон `main`: [`8145a82`](https://github.com/Kirill-Erofeev/development-and-integration-labs/commit/8145a8252febca4b93b7580a40008f508aeb9e68), точный HEAD `8145a8252febca4b93b7580a40008f508aeb9e68`.
Его SHA совпадает с CI и delivery на main. Общий статус локального прогона —
`passed`; идентификатор `79b49183227f4e05bc4ca6ca79c424bd`.

Полный фактический stdout pytest:

```text
........................................................................ [ 75%]
.......................                                                  [100%]
95 passed in 15.75s
```

Восемь HTTP-сценариев выполнены через отдельный реальный Uvicorn:

| Сценарий | Метод | HTTP | Результат |
| --- | --- | --- | --- |
| `baseline.health` | `GET` | `200` | passed |
| `baseline.predict` | `POST` | `200` | passed |
| `baseline.missing_field` | `POST` | `422` | passed |
| `baseline.string_number` | `POST` | `422` | passed |
| `baseline.boolean` | `POST` | `422` | passed |
| `baseline.negative_number` | `POST` | `422` | passed |
| `baseline.docs` | `GET` | `200` | passed |
| `baseline.openapi` | `GET` | `200` | passed |

Runtime-файлы совпали с версией `fdc377f`, для которой
подтверждены Linux/Docker/Compose; здесь дополнительно проверены полный pytest
и восемь HTTP-сценариев. Отдельные результаты feature-клона выше сохраняют
собственный SHA и область проверки.

[FINAL_MAIN_20260929.json](FINAL_MAIN_20260929.json) и
[FINAL_MAIN_20260929.log](FINAL_MAIN_20260929.log) содержат результаты финальной
проверки: точные команды, stdout/stderr и ответы HTTP. Поле `commands_log` сохраняет исходное имя;
его диапазоны байтов относятся к опубликованному `FINAL_MAIN_20260929.log`.
