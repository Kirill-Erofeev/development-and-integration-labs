# Практика 7. CI-конвейер GitHub Actions

Цель — воспроизводимо проверить проект и собрать образы API и клиента из зафиксированной версии репозитория. Реализация: [`.github/workflows/ci.yaml`](../.github/workflows/ci.yaml). Общая подготовка окружения описана в [README проекта](../README.md), состояние проверок — в [README семинара](README.md).

## События и jobs

Workflow запускается при `push` в `main`, при создании, повторном открытии или обновлении `pull_request`, а также вручную через `workflow_dispatch`. Для pull request GitHub по умолчанию проверяет результат предполагаемого слияния. Новый запуск в той же группе `workflow/ref` отменяет предыдущий незавершённый запуск.

| Job | Действия | Условие и ограничения |
| --- | --- | --- |
| `check` | Checkout; Python 3.11; установка двух файлов фиксированных зависимостей; проверка синтаксиса; полный `pytest` | Запускается первой, `ubuntu-24.04`, до 15 минут |
| `build-image` | Новый checkout; сборка `ml-api:test-<SHA>` из корня и `ml-client:test-<SHA>` из `client/` | `needs: check`: только после успешной проверки, до 20 минут |

В `check` используются `requirements.txt` и `client/requirements.txt`. Pip-кэш учитывает оба файла. Синтаксис проверяется для `app`, `src`, `scripts`, `tests` и `client`; `python -m pytest -q` использует общий `pytest.ini`. Сервер Uvicorn и браузер для этих тестов вручную не запускаются.

Образы собираются последовательно на GitHub-hosted runner; сбой первой сборки останавливает job. Для API Dockerfile получает контекст `.` с `app`, `src` и `models`; для клиента контекстом служит `client/`. Dockerfile API задаёт `ML_MODEL_PATH=/app/models/model.pkl`, внутренний порт API — 8000. Образы остаются на временном runner и не публикуются в registry.

Обе jobs имеют `contents: read`, checkout отключает сохранение учётных данных. Actions закреплены полными SHA официальных релизов `checkout v7.0.1` и `setup-python v7.0.0`. Установка зависимостей и загрузка базового Docker-образа требуют сети; отдельные секреты registry для этого сценария не предусмотрены.

## Как воспроизвести и запустить

Из корня проекта, в окружении Python 3.11:

```bash
python --version
python -m pip install --only-binary=:all: -r requirements.txt -r client/requirements.txt
python -m compileall -q app src scripts tests client
python -m pytest -q
docker build --file Dockerfile --tag ml-api:local-check .
docker build --file client/Dockerfile --tag ml-client:local-check client
```

При доступном actionlint статическую проверку можно повторить командой:

```bash
actionlint -shellcheck= -pyflakes= .github/workflows/ci.yaml .github/workflows/delivery.yaml
```

Эта команда отключает внешние ShellCheck и Pyflakes. Она проверяет YAML и правила GitHub Actions, но не исполняет Python, Bash, Docker или HTTP-запросы. Локально также выполнен отдельный разбор Bash через `bash -n`; это проверка синтаксиса без выполнения команд.

Для демонстрации работы с изменениями создайте рабочую ветку, внесите правки workflow и откройте pull request в `main`. В GitHub откройте **Actions → CI**, проверьте логи обеих jobs. Ручной запуск доступен через **Run workflow**, когда файл workflow присутствует в основной ветке. После завершения сохраните URL конкретного запуска, SHA версии и снимки результатов `check` и `build-image`.

**Подтверждённый CI:** [CI #36596424256](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596424256); event `push`, ref `main`,
SHA `8145a8252febca4b93b7580a40008f508aeb9e68`. Jobs `check` и `build-image`, pytest и оба шага сборки
завершились успешно. Фактический pytest: **95 passed in 5.13s**. Реализация слита через [PR #6](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/6).

[Снимок CI](screenshots/practice7-ci.png), [полный лог](CI_20260929.log),
[метаданные и jobs](CI_20260929.json). Новый клон этой main-версии прошёл
**95 passed in 15.75s** и восемь реальных HTTP-сценариев; [протокол](CHECKS.md).

<!-- local-clone-20260929:start -->
## Локальная проверка из чистого клона

29.09.2026 проверен опубликованный [`fdc377f`](https://github.com/Kirill-Erofeev/development-and-integration-labs/commit/fdc377f0d347f3ee1232871f07787daa4ad8b0e7).
Полный pytest из клона: Windows — **95 passed in 10.66s**, Linux —
**95 passed in 18.70s**. Linux использовал `3.11.16 (main, Sep 19 2026, 01:04:43) [GCC 14.2.0]`;
`pip check` завершился сообщением `No broken requirements found.`.

Из этого же клона успешно собраны API и клиент, выполнены реальные HTTP- и
Compose-проверки, ошибка `localhost`, исправление адреса и проверка сохранности
результата после `down`. Полные выводы и JSON: [CHECKS.md](CHECKS.md).
Эти локальные проверки подтверждают код, зависимости и контейнеры выбранного SHA;
события и jobs GitHub фиксируются отдельным URL CI run.
<!-- local-clone-20260929:end -->

## Самопроверка перед защитой

| Вопрос | Краткое объяснение |
| --- | --- |
| Чем различаются workflow, job и step? | Workflow описывает весь сценарий; job выполняется на выделенном runner; steps выполняются последовательно внутри job. |
| Почему YAML хранится в репозитории? | Правила проверки версионируются вместе с кодом и доступны для review. |
| Зачем `needs: check`? | Ошибка тестов не должна приводить к успешной сборке следующей job. При неуспешной `check` зависимая job пропускается. |
| Что такое build context? | Набор доступных Dockerfile файлов. Он задаётся последним аргументом `docker build`, а не расположением самого Dockerfile. |
| Почему здесь нет Kaniko? | Сборка выполняется на GitHub-hosted Ubuntu с Docker. Ограничение исходного runner GitVerse сюда не переносится. |
| Что делает `.dockerignore`? | Исключает ненужные файлы из контекста: например, Git, окружения и кэши. Нужные приложению код и модель должны оставаться доступны сборке. |
| Что означают `runs-on`, `steps` и `github.workspace`? | Выбор runner, последовательность действий и путь checkout на runner. Текущий workflow выполняет команды из корня checkout. |
| Что подтверждает зелёный `build-image`? | Успешную сборку обоих образов для этой версии. Запуск контейнеров и реальную доставку эта job не проверяет. |

Официальные материалы, сверенные 29.09.2026: [синтаксис GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax), [события запуска](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows), [checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1), [setup-python v7.0.0](https://github.com/actions/setup-python/releases/tag/v7.0.0).
