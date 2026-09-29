# Практика 8. Доставка и откат в режиме dry run

Цель — передать одну версию между jobs, дождаться проверок и показать порядок обновления API и отката. Реализация: [`.github/workflows/delivery.yaml`](../.github/workflows/delivery.yaml). Внешняя тестовая среда для этой практики не предусмотрена; команды доставки выводятся в лог.

## Ручной запуск и порядок jobs

Workflow имеет только событие `workflow_dispatch`. После появления файла в основной ветке откройте **Actions → Delivery Dry Run → Run workflow**, выберите `main` и запустите сценарий. Выбирайте версию, для которой уже проверен [CI практики 7](PRACTICE_7.md): автоматической связи между результатами двух workflow нет.

```text
build ─┬─ smoke_api_tests_stub ─┬─ deploy_dry_run
       └─ docs_checks ──────────┘
```

| Job | Что выполняется | Зависимость |
| --- | --- | --- |
| `build` | Проверяет формат `GITHUB_SHA`, формирует `test-<SHA>`, записывает `image-tag` в `$GITHUB_OUTPUT` | Первая job; здесь нет сборки или публикации образа |
| `smoke_api_tests_stub` | Получает тег и печатает команды GET `/health` и POST `/predict` | Только `needs: build`; HTTP-запросы не выполняются |
| `docs_checks` | Выполняет checkout, затем `test -f README.md` | Только `needs: build`; содержательность документации проверяется отдельно |
| `deploy_dry_run` | Печатает обновление, smoke test и откат | Ожидает `build` и обе проверки; `success()` и `github.ref == 'refs/heads/main'` |

Две проверочные jobs могут идти параллельно: между ними нет `needs`. Их фактическое одновременное выполнение зависит от доступности runners. При ошибке зависимости доставка пропускается. При ручном запуске из другой ветки первые три jobs могут выполниться, но `deploy_dry_run` будет пропущена. Во всех jobs используется `ubuntu-24.04`, timeout — 5 минут; права workflow ограничены `contents: read`.

Output шага `set_tag` становится output job `build`, затем передаётся как `needs.build.outputs.image-tag` в переменную окружения `IMAGE_TAG`. Так все последующие действия используют одну версию. Значение не вставляется непосредственно в текст Bash из выражения GitHub; перед печатью доставки формат тега повторно проверяется.

## Что должно появиться в логе

Workflow использует фиктивное имя `registry.example.invalid/ml-api`, контейнер `ml-api-test`, предыдущий тег `previous-stable`. Эти обозначения не требуют существующего registry. CI собирает два образа, а учебный сценарий доставки показывает обновление только API; образы из CI в delivery не передаются.

Порядок печатаемых команд:

1. `docker pull` для `test-<SHA>` до остановки текущего контейнера.
2. `docker stop` и `docker rm` для `ml-api-test`.
3. `docker run` с портом `127.0.0.1:8080:8000` и `ML_MODEL_PATH=/app/models/model.pkl`.
4. GET `http://127.0.0.1:8080/health` и POST `http://127.0.0.1:8080/predict`.
5. Предлагаемый откат: pull `previous-stable`, stop, rm, run с прежними параметрами, GET `/health`.

Синтетическое тело POST соответствует четырём положительным числовым признакам API:

```json
{"sepal_length":5.1,"sepal_width":3.5,"petal_length":1.4,"petal_width":0.2}
```

`curl --fail-with-body --max-time 10` в напечатанном примере задаёт ограничение времени и ошибку при неуспешном HTTP-ответе. Даже эти запросы здесь не выполняются. Печать отката происходит в каждом успешном dry-run; автоматической реакции на реальную ошибку сервиса нет.

## Откат и переход к реальной среде

В реальном процессе предыдущая проверенная версия должна храниться в журнале развёртываний как неизменяемый тег или digest. Перед остановкой сервиса нужно получить её образ, а после восстановления проверить готовность и ответы API. `previous-stable` в учебном workflow — только условное обозначение этой версии.

Чтобы реализовать доставку позже, понадобятся согласованная тестовая среда, публикация проверенного образа, защищённая настройка доступа к среде и registry, ожидание готовности API и обработка неуспешных smoke tests. Сценарий следует связать с успешным CI той же версии. Эти изменения требуют отдельной реализации; текущий workflow не подключается по SSH, не использует секреты, не выполняет Docker/curl и не изменяет сервисы.

<!-- local-delivery-20260929:start -->
## Локально выполненные проверки

29.09.2026 исполнены все шесть Bash-блоков версии
[`fdc377f`](https://github.com/Kirill-Erofeev/development-and-integration-labs/commit/fdc377f0d347f3ee1232871f07787daa4ad8b0e7) с синтетическим контекстом GitHub;
каждый завершился с кодом `0`. Подтверждены `test-fdc377f0d347f3ee1232871f07787daa4ad8b0e7`,
наличие README, `ML_MODEL_PATH`, полный POST и команды отката к `previous-stable`.
Docker и curl в delivery-блоках только печатаются.

Полный фактический вывод: [DELIVERY_20260929.log](DELIVERY_20260929.log).
В отдельной проверке тот же опубликованный клон прошёл **95 passed in 18.70s**
на Linux и реальный Compose-сценарий; см. [CHECKS.md](CHECKS.md).
Оркестрация, граф jobs и условия ветвей GitHub подтверждаются реальными workflow runs.
<!-- local-delivery-20260929:end -->

## Доказательства и самопроверка

После реального ручного запуска сохраните URL run, выбранную ветку и SHA, граф jobs, сформированный `image-tag`, логи предложенного обновления, двух HTTP-запросов и отката. Для проверки ограничения ветки можно отдельно запустить workflow на рабочей ветке и зафиксировать пропуск `deploy_dry_run`.

**Delivery на main:** [Delivery main #36596835394](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596835394), SHA `8145a8252febca4b93b7580a40008f508aeb9e68`:
`build`, `smoke_api_tests_stub`, `docs_checks`, `deploy_dry_run` — `success`.
**Проверка другой ветки:** [Delivery feature #36596569372](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596569372), ref `feature/delivery-dry-run`,
SHA `fdc377f0d347f3ee1232871f07787daa4ad8b0e7`: первые три jobs — `success`, `deploy_dry_run` — `skipped`.
Реализация слита через [PR #7](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/7); в логе main подтверждены единый тег
`test-8145a8252febca4b93b7580a40008f508aeb9e68`, путь модели и команды отката.

[Снимок main](screenshots/practice8-delivery.png),
[снимок feature](screenshots/practice8-branch.png),
[лог main](DELIVERY_MAIN_20260929.log), [лог feature](DELIVERY_BRANCH_20260929.log).
Метаданные jobs и проверка итогового клона — в [CHECKS.md](CHECKS.md). Успех dry-run подтверждает порядок jobs и формирование команд; обновление сервиса и HTTP-ответы этим не доказаны.

| Вопрос | Краткое объяснение |
| --- | --- |
| Почему запуск ручной? | Выбор версии доставки отделён от каждого изменения кода и делается явно. |
| Чем CI отличается от этого CD-сценария? | CI выполняет тесты и сборки; delivery моделирует последующие действия для выбранного тега. |
| Зачем нужны outputs и `needs`? | Output передаёт версию, а `needs` задаёт зависимости и условия перехода между jobs. |
| Что проверяет `success()`? | Успешность обязательных предыдущих jobs; дополнительные условия также требуют ветку `main`. |
| Почему README проверяется после checkout? | Каждая job получает отдельную рабочую среду; checkout другой job не создаёт здесь файлы. |
| Почему не требуются сервер и секреты? | Docker и HTTP-команды только выводятся в лог, а адрес registry фиктивный. |
| Что потребуется защитить при реальной доставке? | Учётные данные доступа к registry и среде, например токен registry и ключ доступа; их нельзя помещать в репозиторий или логи. |
| Почему необходим предыдущий тег? | Он однозначно задаёт проверенную версию для восстановления после неудачного обновления. |

Официальные материалы, сверенные 29.09.2026: [передача outputs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/pass-job-outputs), [ручной запуск](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch), [параметры docker run](https://docs.docker.com/reference/cli/docker/container/run/).
