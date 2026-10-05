# Практика 7 — GitHub Actions CI

## Требование и реализация

Платформа адаптирована к GitHub по решению владельца репозитория.
Действующий файл — `.github/workflows/ci.yaml`, workflow **CI**.
Он запускается при pull request, push в `main` и по `workflow_dispatch`.

Job `check` устанавливает Python 3.11 и зависимости из корневого и клиентского
requirements, выполняет `compileall` и полный pytest. Job `build-image`
зависит от успеха `check` и собирает API и клиент с тегами `test-<SHA>`.
У workflow только `contents: read`; checkout не сохраняет credentials.
Действия закреплены на конкретных upstream SHA в YAML.

## Локальная предварительная проверка

```powershell
py -3.11 -m pip install -r requirements.txt -r client/requirements.txt
py -3.11 -m compileall -q app src scripts tests client
py -3.11 -m pytest -q
docker build --file Dockerfile --tag ml-api:ci-check .
docker build --file client/Dockerfile --tag ml-client:ci-check client
```

Если доступен `actionlint`, проверьте `.github/workflows/ci.yaml` и сохраните его
версию и код завершения. Локальные результаты не заменяют фактический GitHub run.

## Проверка pull request и main

1. В новом PR дождаться `check` и `build-image`; сохранить новый URL run и проверенный SHA.
2. Открыть логи, проверить фактическое число тестов и обе сборки, а не только зелёный значок.
3. После merge проверить отдельный автоматический run на `main` и его SHA.
4. В протоколе различать PR merge ref и коммит `main`: это разные запуски.

Сборки создают образы на временном runner. CI не загружает их в registry и не
развёртывает сервис. Проверку реального контейнера подтверждают материалы практик 5–6.

## Проверки и материалы сдачи

Статус: **фактический прогон выполнен; результаты и проверенный SHA приведены в CHECKS.md**. Команды и ожидаемые результаты
выше являются проверочным сценарием, а не протоколом уже выполненной проверки.
Фактические команды, коды завершения, версия Python, проверенный commit, результаты
и ссылки на новые PR/runs добавляются в [CHECKS.md](CHECKS.md).

Планируемые снимки после успешных проверок:

- [practice7-ci.png](screenshots/practice7-ci.png).
- [practice7-build.png](screenshots/practice7-build.png).

Ссылка считается подтверждением только после добавления соответствующего файла.
Снимки фиксируют проверенный коммит; последующее добавление материалов сдачи
не должно подменять его другим состоянием кода. Старые прогоны не подтверждают этот этап.
Word-отчёт оформляется пользователем отдельно после получения снимков.
