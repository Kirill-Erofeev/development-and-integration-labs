# Протоколы проверок

Ниже сохранены протоколы фактических проверок. Незавершённые этапы обозначены отдельно. Записи ранних практик при
добавлении следующей сохраняются; старые SHA и runs из прежней истории не переносятся.

## Контейнер API — фактическая проверка

Проверенный коммит: `a8a0fa9d529b31f40608bf38154b2dccc0e623fe`. Дата: 2026-10-05T12:22:24.484245+03:00.

| Проверка | Фактический код | Результат |
| --- | --- | --- |
| Сборка образа | 0 | succeeded |
| Запуск | 0 | succeeded |
| Готовность | 0 | succeeded |
| Состояние контейнера | 0 | succeeded |
| Контрольное предсказание | 0 | succeeded |
| Логи API | 0 | succeeded |
| Остановка | 0 | succeeded |
| Повторный старт | 0 | succeeded |
| Повторная готовность | 0 | succeeded |
| Повторное предсказание | 0 | succeeded |
| Завершение стенда | 0 | succeeded |
| Удаление своего контейнера | 0 | succeeded |

[Полный журнал](evidence/practice5-20261005-122224/commands.log), [манифест](evidence/practice5-20261005-122224/manifest.json).

![practice5-build](screenshots/practice5-build.png)

![practice5-runtime](screenshots/practice5-runtime.png)

![practice5-repeat](screenshots/practice5-repeat.png)

## Docker Compose — фактическая проверка

Проверенный коммит: `b438ea1d47b418836390616d67654b9bfcb324e5`. Дата: 2026-10-05T12:24:22.312292+03:00.

| Проверка | Фактический код | Результат |
| --- | --- | --- |
| Сборка API и клиента | 0 | succeeded |
| Запуск Compose | 0 | succeeded |
| Готовность API | 0 | succeeded |
| Завершение клиента | 0 | succeeded |
| Состояния сервисов | 0 | succeeded |
| Логи сервисов | 0 | succeeded |
| Результат клиента | 0 | succeeded |
| Неверный адрес API | 1 | expected_failure |
| Остановка Compose | 0 | succeeded |
| Сохранность результата | 0 | succeeded |

[Полный журнал](evidence/practice6-20261005-122422/commands.log), [манифест](evidence/practice6-20261005-122422/manifest.json).

![practice6-status](screenshots/practice6-status.png)

![practice6-localhost](screenshots/practice6-localhost.png)

![practice6-persistence](screenshots/practice6-persistence.png)
