# Публикация практик 2–4 в GitHub

Обновление: 29.09.2026. Репозиторий — [development-and-integration-labs](https://github.com/Kirill-Erofeev/development-and-integration-labs).
Первые три PR последовательно слиты в `main` обычными merge commits.
Номера, ссылки, SHA исходных веток и merge commits взяты из сохранённых
подтверждений GitHub.
Публикация учебных CSV/ZIP и создание новых копий при проверках явно разрешены
пользователем в текущем диалоге. Дополнительного ожидания разрешения нет.

## Подтверждённые PR практик 2–4

| PR | Изменение | Ветка → base | Исходный SHA ветки | Состояние | Merge commit |
| --- | --- | --- | --- | --- | --- |
| [PR #1](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/1) | feat(cli): добавить выбор формата вывода предсказаний | `feature/predict-output-format` → `main` | `1c6750e9bea04ca417f4c692e599ab92c80d21c4` | Слит | [`63c2cc3`](https://github.com/Kirill-Erofeev/development-and-integration-labs/commit/63c2cc31e86204ef59613b03bff72ce1b8eb7b06) |
| [PR #2](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/2) | feat(api): добавить HTTP-интерфейс модели Iris | `feature/model-api` → `main` | `954b603b1a1872c9913c3e1d0c7ca226fb97fbb9` | Слит | [`96a4bae`](https://github.com/Kirill-Erofeev/development-and-integration-labs/commit/96a4baefad0f9c4a204ee7caf689fb3344596ea0) |
| [PR #3](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/3) | test(api): проверить HTTP-контракты и ошибки модели | `feature/api-tests` → `main` | `c5470cb6e090bfb4a1cd0909c9394de08face525` | Слит | [`dea7853`](https://github.com/Kirill-Erofeev/development-and-integration-labs/commit/dea785300a237fd1da659c1c40530b8486b73768) |

## Дополнительные PR по сохранённым данным

| PR | Изменение | Ветка → base | Исходный SHA ветки | Состояние | Merge commit |
| --- | --- | --- | --- | --- | --- |
| [PR #4](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/4) | build(api): контейнеризировать сервис на Python 3.11 | `feature/api-container` → `main` | `6bf9916d0b552010bb248d0713d022412ddf0ca3` | Слит | [`d172469`](https://github.com/Kirill-Erofeev/development-and-integration-labs/commit/d172469993f6e30b948b74aed6a5606accf9274c) |
| [PR #5](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/5) | feat(compose): связать API и клиент через Docker Compose | `feature/compose-client` → `main` | `0d155ffe760abff5f0583a1cf915e5d1c515c443` | Слит | [`eb09789`](https://github.com/Kirill-Erofeev/development-and-integration-labs/commit/eb0978942952983539a750744cebb462a4eb67ad) |
| [PR #6](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/6) | ci(github): добавить проверки и сборку двух образов | `feature/github-ci` → `main` | `48f9f1f765801366989d03a265e75412342ce28e` | Слит | [`eb69020`](https://github.com/Kirill-Erofeev/development-and-integration-labs/commit/eb69020bd7b6a02b7e9b925ee32656273723ca2a) |
| [PR #7](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/7) | ci(delivery): добавить ручную имитацию доставки | `feature/delivery-dry-run` → `main` | `fdc377f0d347f3ee1232871f07787daa4ad8b0e7` | Слит | [`8145a82`](https://github.com/Kirill-Erofeev/development-and-integration-labs/commit/8145a8252febca4b93b7580a40008f508aeb9e68) |

## Учебный саморазбор

Учебный разбор включён в тело [PR #1](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/1) как саморазбор выполненной работы.
Это не отзыв другого участника и не отдельный опубликованный review-комментарий.
Замечание относится к проверке неизменности исходного списка и вложенных словарей:
до форматирования нужна независимая копия через `deepcopy`, после — сравнение.
Исправление уже присутствовало в историческом коммите `007b270`.

## Исторические результаты этапа 18.09.2026

- Практика 2: сначала прошли 25 тестов, после дополнения проверки неизменности — 27.
  Реальный конфликт README разрешён merge `1c6750e`; diff и PNG сохранены
  в [практике 2](PRACTICE_2.md).
- Практика 3: выполнены восемь сценариев настоящего HTTP-сервера; ответы и снимки
  приведены в [практике 3](PRACTICE_3.md).
- Практика 4: после выноса fixtures — **55 passed in 8.98s**;
  описание проверки и исправления импорта находится в [практике 4](PRACTICE_4.md).

Эти результаты относятся к версиям первых практик и не заменяются результатами
последующего полного набора. Сохранённые diff и изображения не изменены.

## Подтверждённая проверка feature-клона

Подтверждён новый клон `feature/delivery-dry-run` на коммите `fdc377f`: Windows — **95 passed in 10.66s**, Linux — **95 passed in 18.70s**. Полный прогон Docker/Compose описан в [CHECKS.md семинара 25.09.2026](<../Семинар 25.09.2026/CHECKS.md>). Эти результаты относятся к feature-версии, а не к итоговой `main`. Итоговый клон `main` на коммите [`8145a82`](https://github.com/Kirill-Erofeev/development-and-integration-labs/commit/8145a8252febca4b93b7580a40008f508aeb9e68) (`8145a8252febca4b93b7580a40008f508aeb9e68`) проверен: **95 passed in 15.75s** и **8 реальных HTTP-сценариев**. Протокол: [CHECKS.md семинара 25.09.2026](<../Семинар 25.09.2026/CHECKS.md>).

## Подтверждённая проверка итоговой main

Итоговый клон `main` на коммите [`8145a82`](https://github.com/Kirill-Erofeev/development-and-integration-labs/commit/8145a8252febca4b93b7580a40008f508aeb9e68) (`8145a8252febca4b93b7580a40008f508aeb9e68`) проверен: **95 passed in 15.75s** и **8 реальных HTTP-сценариев**. Протокол: [CHECKS.md семинара 25.09.2026](<../Семинар 25.09.2026/CHECKS.md>).
Команды выполняются из корня клона; для Windows используется глобальный
`py -3.11`. Проверка клона не означает создание чистого Python-окружения.
