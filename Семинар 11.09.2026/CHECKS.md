# Протоколы проверок

Ниже сохранены протоколы фактических проверок. Незавершённые этапы обозначены отдельно. Записи ранних практик при
добавлении следующей сохраняются; старые SHA и runs из прежней истории не переносятся.

## Git и коллективная разработка — фактическая проверка

Проверенный коммит: `adc79831a6c5c205d9071603b290dd1e30583872`. Дата: 2026-10-05T12:14:42.492506+03:00.

| Проверка | Фактический код | Результат |
| --- | --- | --- |
| Формат JSON | 0 | succeeded |
| Формат text | 0 | succeeded |
| Граф Git | 0 | succeeded |
| pytest | 0 | succeeded |

[Полный журнал](evidence/practice2-20261005-121442/commands.log), [манифест](evidence/practice2-20261005-121442/manifest.json).

[Новый pull request](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/23).

Учебный конфликт получен командой merge с фактическим кодом 1 и разрешён коммитом `adc79831a6c5c205d9071603b290dd1e30583872`. [Журнал конфликта](evidence/practice2-conflict-20261005-121436/commands.log).

Саморазбор в PR выявил отсутствие теста неизменности входного списка; добавлены проверки обоих форматов.

![Учебный конфликт](screenshots/practice2-conflict.png)

![practice2-cli](screenshots/practice2-cli.png)

![practice2-git](screenshots/practice2-git.png)

## HTTP API модели — фактическая проверка

Проверенный коммит: `8936a2ffea5de9ef4b2071c3b60d9fdf6fa67672`. Дата: 2026-10-05T12:16:10.859600+03:00.

| Проверка | Фактический код | Результат |
| --- | --- | --- |
| Готовность модели | 0 | succeeded |
| Контрольный прогноз | 0 | succeeded |
| Ошибка валидации | 0 | succeeded |
| Журнал Uvicorn | 0 | succeeded |

[Полный журнал](evidence/practice3-20261005-121610/commands.log), [манифест](evidence/practice3-20261005-121610/manifest.json).

![practice3-docs](screenshots/practice3-docs.png)

![practice3-startup](screenshots/practice3-startup.png)

![practice3-health](screenshots/practice3-health.png)

![practice3-predict](screenshots/practice3-predict.png)

## Модульные и интеграционные тесты — фактическая проверка

Проверенный коммит: `aeb903054c467aa149a42b6f2b6968cd8f99460d`. Дата: 2026-10-05T12:21:06.847499+03:00.

| Проверка | Фактический код | Результат |
| --- | --- | --- |
| pytest | 0 | succeeded |

[Полный журнал](evidence/practice4-20261005-122106/commands.log), [манифест](evidence/practice4-20261005-122106/manifest.json).

![practice4-pytest](screenshots/practice4-pytest.png)
