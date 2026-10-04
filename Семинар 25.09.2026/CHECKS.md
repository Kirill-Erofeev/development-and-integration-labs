# Протоколы проверок

Ниже сохранены протоколы фактических проверок. Незавершённые этапы обозначены отдельно. Записи ранних практик при
добавлении следующей сохраняются; старые SHA и runs из прежней истории не переносятся.

## Практика 8: Учебная доставка

Статус: **ожидает фактической проверки этапа**.

- Проверенный новый commit: не заполнен.
- Дата, ОС, Python и версии инструментов: не заполнены.
- Команды, коды завершения и итог тестов: не заполнены.
- Новый PR и workflow runs, если применимо: не заполнены.
- Саморазбор и внешнее ревью: фактические результаты не внесены.

- [ ] workflow_dispatch main.
- [ ] передача тега и зависимости jobs.
- [ ] команды доставки и rollback.
- [ ] deploy skipped в feature.

Планируемые снимки:

- [practice8-delivery.png](screenshots/practice8-delivery.png).
- [practice8-branch.png](screenshots/practice8-branch.png).

## GitHub Actions CI — фактическая проверка

Проверенный коммит: `24c715506452ae353494bab7721cce198f549574`. Дата: 2026-10-04T22:00:20.978997+03:00.

| Проверка | Фактический код | Результат |
| --- | --- | --- |
| CI: jobs и steps | 0 | succeeded |
| Журнал CI | 0 | succeeded |

[Полный журнал](evidence/practice7-20261004-220020/commands.log), [манифест](evidence/practice7-20261004-220020/manifest.json).

[Новый pull request](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/15).

![practice7-ci](screenshots/practice7-ci.png)

![practice7-build](screenshots/practice7-build.png)
