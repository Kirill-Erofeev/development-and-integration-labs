# Семинар 11.09.2026: практики 2–4

Работы продолжают [проект семинара 04.09.2026](<../README.md>).
Код, модель, зависимости и тесты находятся в том проекте; здесь остаются
исходные задания, результаты и скриншоты. Используется глобальный `py -3.11`.

Результаты этапа 18.09.2026:

| Работа | Реализация и проверка |
| --- | --- |
| [Практика 2](PRACTICE_2.md) | JSON/text в CLI, ветки, учебное review, настоящий конфликт README |
| [Практика 3](PRACTICE_3.md) | FastAPI сохранённой модели, схемы, 8 проверок реального HTTP-сервера |
| [Практика 4](PRACTICE_4.md) | Fixtures, unit/API/integration тесты; всего 55 прошедших сценариев |

Word-отчёты отменены; исторические результаты сохранены в Markdown и Git.

Обновление 29.09.2026: [PR #1](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/1), [PR #2](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/2), [PR #3](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/3) слиты в `main` обычными merge commits.
Учебный саморазбор размещён в теле первого PR; это не отзыв другого участника.

Подтверждён новый клон `feature/delivery-dry-run` на коммите `fdc377f`: Windows — **95 passed in 10.66s**, Linux — **95 passed in 18.70s**. Полный прогон Docker/Compose описан в [CHECKS.md семинара 25.09.2026](<../Семинар 25.09.2026/CHECKS.md>). Эти результаты относятся к feature-версии, а не к итоговой `main`. Итоговый клон `main` на коммите [`8145a82`](https://github.com/Kirill-Erofeev/development-and-integration-labs/commit/8145a8252febca4b93b7580a40008f508aeb9e68) (`8145a8252febca4b93b7580a40008f508aeb9e68`) проверен: **95 passed in 15.75s** и **8 реальных HTTP-сценариев**. Протокол: [CHECKS.md семинара 25.09.2026](<../Семинар 25.09.2026/CHECKS.md>).

[План и состояние требований](PLAN.md) · [Подтверждённая публикация](GITHUB.md).
