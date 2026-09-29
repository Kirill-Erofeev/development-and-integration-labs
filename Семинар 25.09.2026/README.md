# Семинар 25.09.2026: CI и учебная доставка

Практики 7–8 продолжают общий ML-проект: FastAPI, Python 3.11, модель `models/model.pkl` и отдельный клиент находятся в корне репозитория. Команды запуска сервиса описаны в [основном README](../README.md).

| Материал | Назначение | Реализация |
| --- | --- | --- |
| [Практика 7](PRACTICE_7.md) | Автоматические проверки и сборка двух образов | [ci.yaml](../.github/workflows/ci.yaml) |
| [Практика 8](PRACTICE_8.md) | Ручная доставка и откат в режиме dry run | [delivery.yaml](../.github/workflows/delivery.yaml) |
| [План и проверки](PLAN.md) | Требования, реализация, доказательства и остаток работы | Действующий план семинара |

Исходные задания описывают GitVerse. Здесь сохранены учебные цели и граф jobs, а платформа заменена на GitHub Actions: `.github/workflows`, контекст `github`, файл `$GITHUB_OUTPUT`, основная ветка `main`. На GitHub-hosted Ubuntu используется Docker; Kaniko в исходном задании нужен из-за отсутствия Docker daemon на runner GitVerse.

CI выполняет реальные тесты и сборки на runner. Delivery печатает предлагаемые команды обновления API, smoke test и отката. Для delivery не нужны внешний сервер, registry или секреты. Эти два workflow независимы: ручной запуск delivery сам по себе не доказывает успех CI, поэтому для демонстрации следует выбирать уже проверенную версию `main`.

Состояние проверки на 29.09.2026:

| Проверка | Подтверждённый результат |
| --- | --- |
| Baseline после переноса проекта в корень | `95 passed in 11.36s` |
| Чистый клон опубликованного `fdc377f`, Windows | `95 passed in 10.66s`; реальные health/predict локального API |
| Тот же клон, Linux | `95 passed in 18.70s`; `Python: 3.11.16 (main, Sep 19 2026, 01:04:43) [GCC 14.2.0]`; `pip check` успешен |
| Docker из чистого клона | Образы API и клиента собраны; Compose API healthy, client exit 0; ошибка адреса и сохранность JSON проверены |
| actionlint 1.7.12 | Оба YAML прошли встроенную проверку, exit 0; внешние ShellCheck и Pyflakes отключены |
| `bash -n` | Разобраны 11 блоков `run` без исполнения команд |
| Локальные Bash-шаги delivery | Все 6 шагов версии `fdc377f` завершились с кодом 0; тег и команды отката проверены |
| Итоговый клон main `8145a82` | `95 passed in 15.75s` и 8 реальных HTTP-сценариев |
| PR и GitHub Actions | Семь PR слиты; [CI #36596424256](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596424256), [Delivery main #36596835394](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596835394), [Delivery feature #36596569372](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596569372): success; deploy в feature пропущен |

Подробный [отчёт проверок](CHECKS.md) содержит фактический pytest-вывод,
версию Python, результаты Compose и ссылки на полные журналы.

## Реальные GitHub Actions и PR

| Запуск | Ref | Проверенный SHA | Результат |
| --- | --- | --- | --- |
| [CI #36596424256](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596424256) | `main` | `8145a8252febca4b93b7580a40008f508aeb9e68` | check/build-image success; `95 passed in 5.13s` |
| [Delivery main #36596835394](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596835394) | `main` | `8145a8252febca4b93b7580a40008f508aeb9e68` | Все четыре jobs success |
| [Delivery feature #36596569372](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596569372) | `feature/delivery-dry-run` | `fdc377f0d347f3ee1232871f07787daa4ad8b0e7` | Три jobs success; deploy_dry_run skipped |

CI опубликован через [PR #6](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/6); delivery — через [PR #7](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/7).
Все семь слитых PR, jobs, логи, JSON и проверка итоговой main — в [CHECKS.md](CHECKS.md).

- [CI](screenshots/practice7-ci.png).
- [Delivery на main](screenshots/practice8-delivery.png).
- [Пропуск deploy на feature](screenshots/practice8-branch.png).
