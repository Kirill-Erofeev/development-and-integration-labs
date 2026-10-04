# Протоколы проверок

Ниже сохранены протоколы фактических проверок. Незавершённые этапы обозначены отдельно. Записи ранних практик при
добавлении следующей сохраняются; старые SHA и runs из прежней истории не переносятся.

## Практика 3: HTTP API модели

Статус: **ожидает фактической проверки этапа**.

- Проверенный новый commit: не заполнен.
- Дата, ОС, Python и версии инструментов: не заполнены.
- Команды, коды завершения и итог тестов: не заполнены.
- Новый PR и workflow runs, если применимо: не заполнены.
- Саморазбор и внешнее ревью: фактические результаты не внесены.

- [ ] запуск.
- [ ] health.
- [ ] predict.
- [ ] ошибка 422.
- [ ] Swagger UI.

Планируемые снимки:

- [practice3-startup.png](screenshots/practice3-startup.png).
- [practice3-health.png](screenshots/practice3-health.png).
- [practice3-predict.png](screenshots/practice3-predict.png).
- [practice3-docs.png](screenshots/practice3-docs.png).

## Практика 4: Модульные и интеграционные тесты

Статус: **ожидает фактической проверки этапа**.

- Проверенный новый commit: не заполнен.
- Дата, ОС, Python и версии инструментов: не заполнены.
- Команды, коды завершения и итог тестов: не заполнены.
- Новый PR и workflow runs, если применимо: не заполнены.
- Саморазбор и внешнее ревью: фактические результаты не внесены.

- [ ] полный pytest.
- [ ] однократная загрузка модели.
- [ ] ошибки API.

Планируемые снимки:

- [practice4-pytest.png](screenshots/practice4-pytest.png).

## Git и коллективная разработка — фактическая проверка

Проверенный коммит: `58e9cf679cf9ef9baac3bcaaf77e69d1beb15bdf`. Дата: 2026-10-04T21:44:46.848862+03:00.

| Проверка | Фактический код | Результат |
| --- | --- | --- |
| Формат JSON | 0 | succeeded |
| Формат text | 0 | succeeded |
| Граф Git | 0 | succeeded |
| pytest | 0 | succeeded |

[Полный журнал](evidence/practice2-20261004-214446/commands.log), [манифест](evidence/practice2-20261004-214446/manifest.json).

[Новый pull request](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/9).

Учебный конфликт получен командой merge с фактическим кодом 1 и разрешён коммитом `58e9cf679cf9ef9baac3bcaaf77e69d1beb15bdf`. [Журнал конфликта](evidence/practice2-conflict-20261004-214357/commands.log).

Саморазбор в PR выявил отсутствие теста неизменности входного списка; добавлены проверки обоих форматов.

![Учебный конфликт](screenshots/practice2-conflict.png)

![practice2-cli](screenshots/practice2-cli.png)

![practice2-git](screenshots/practice2-git.png)
