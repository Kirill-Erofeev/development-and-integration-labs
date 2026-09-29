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
actionlint -shellcheck= -pyflakes= .github/workflows/ci.yaml
```

Эта команда отключает внешние ShellCheck и Pyflakes. Она проверяет YAML и правила GitHub Actions, но не исполняет Python, Bash, Docker или HTTP-запросы. Локально также выполнен отдельный разбор Bash через `bash -n`; это проверка синтаксиса без выполнения команд.

Для демонстрации работы с изменениями создайте рабочую ветку, внесите правки workflow и откройте pull request в `main`. В GitHub откройте **Actions → CI**, проверьте логи обеих jobs. Ручной запуск доступен через **Run workflow**, когда файл workflow присутствует в основной ветке. После завершения сохраните URL конкретного запуска, SHA версии и снимки результатов `check` и `build-image`.

**Ссылка на успешный CI run:** ожидает фактического запуска. Локальная проверка: 95 тестов после переноса проекта в корень; actionlint завершился с кодом 0.

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
