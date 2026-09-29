# План и результаты семинара 25.09.2026

Статус: **действует**. Дата: **29.09.2026**. Runtime находится в корне репозитория.
Проверенная опубликованная версия: [`fdc377f`](https://github.com/Kirill-Erofeev/development-and-integration-labs/commit/fdc377f0d347f3ee1232871f07787daa4ad8b0e7),
ветка `feature/delivery-dry-run`. GitVerse в практиках 7–8 адаптирован к GitHub Actions.

| Требование | Реализация | Проверка и текущий статус | Артефакт |
| --- | --- | --- | --- |
| Проверить полный pytest и зависимости | Python 3.11, requirements и job check | CI `95 passed in 5.13s`; итоговая main `95 passed in 15.75s`; исходный feature-клон Windows/Linux сохранён в отчёте | [CI #36596424256](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596424256), [CHECKS.md](CHECKS.md) |
| Собрать оба образа после тестов | needs check; API и client | CI check/build-image и оба шага сборки success | [CI #36596424256](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596424256), [CI_20260929.log](CI_20260929.log) |
| Подтвердить интеграцию | Compose, healthcheck, сеть, bind mount | API healthy, client exit 0; localhost exit 1; исправление exit 0; JSON сохранился после down | [CHECKS.md](CHECKS.md) |
| CI по push, PR и вручную | Три события в ci.yaml | Реальный запуск: event `push`, ref main, conclusion success; YAML проверен actionlint | [CI #36596424256](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596424256), [PR #6](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/6) |
| Ручная доставка и ограничение main | workflow_dispatch и условие main | На main четыре jobs success; на feature deploy skipped, остальные success | [Delivery main #36596835394](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596835394), [Delivery feature #36596569372](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596569372) |
| Один тег и outputs | test-SHA, GITHUB_OUTPUT и IMAGE_TAG | В реальном delivery подтверждён `test-8145a8252febca4b93b7580a40008f508aeb9e68` | [DELIVERY_MAIN_20260929.log](DELIVERY_MAIN_20260929.log) |
| Параллельные проверочные jobs | Обе зависят только от build | Обе jobs завершились success; времена jobs сохранены в JSON | [Delivery main #36596835394](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596835394), [DELIVERY_MAIN_20260929.json](DELIVERY_MAIN_20260929.json) |
| Учебная доставка и откат | Печать Docker/curl и previous-stable | Реальный deploy_dry_run success; команды и откат присутствуют в логе | [Delivery main #36596835394](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596835394) |
| Ограничить workflow | contents read, timeout, закреплённые SHA actions | Проверено по YAML; внешние ShellCheck и Pyflakes отключены | Оба workflow |
| Зафиксировать доказательства | Markdown, PNG, JSON и журналы | PR, три Actions run и итоговый main-клон подтверждены | [CHECKS.md](CHECKS.md), screenshots/ |

Проверенный локально actionlint **1.7.12** получен из официального Windows amd64 release, SHA256 архива сверена с официальным `checksums.txt`. Команда проверки двух workflow завершилась с кодом 0 после исправления YAML-команды установки зависимостей. Внешние анализаторы ShellCheck и Pyflakes были отключены; это не полный прогон всех возможных линтеров. Отдельный `bash -n` подтвердил синтаксис 11 блоков `run` без исполнения их команд.

## Выполненные внешние проверки

- CI на `main`: [CI #36596424256](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596424256); pytest `95 passed in 5.13s`, обе сборки успешны.
- Delivery на `main`: [Delivery main #36596835394](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596835394); все четыре jobs успешны.
- Delivery на feature: [Delivery feature #36596569372](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/36596569372); deploy пропущен, остальные jobs успешны.
- Семь PR слиты; [история публикации](<../Семинар 11.09.2026/GITHUB.md>).
- Новый клон `main` `8145a8252febca4b93b7580a40008f508aeb9e68`: `95 passed in 15.75s` и восемь HTTP-сценариев.

Полные подтверждения — [CHECKS.md](CHECKS.md). Учебный delivery выводит команды;
обновление внешнего сервиса этим workflow не выполняется.
