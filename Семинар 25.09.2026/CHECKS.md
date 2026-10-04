# Протоколы проверок

Ниже сохранены протоколы фактических проверок. Незавершённые этапы обозначены отдельно. Записи ранних практик при
добавлении следующей сохраняются; старые SHA и runs из прежней истории не переносятся.

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

Дополнительно проверен [CI после merge в main](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/37227333312) для `85d60d16c1a9926f3eac4ed0927cc2e1005bd809`: все jobs завершены успешно. Метаданные — [github-run.json](evidence/practice7-main/github-run.json).

## Учебная доставка — фактическая проверка

Проверенный коммит: `aa2034da76c590e8305b08b1b8f32616db11c0a9`. Дата: 2026-10-04T22:13:39.175043+03:00.

| Проверка | Фактический код | Результат |
| --- | --- | --- |
| Workflow main | 0 | succeeded |
| Доставка, smoke и rollback | 0 | succeeded |
| Workflow feature | 0 | succeeded |

[Полный журнал](evidence/practice8-20261004-221338/commands.log), [манифест](evidence/practice8-20261004-221338/manifest.json).

[Новый pull request](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/16).

![practice8-delivery](screenshots/practice8-delivery.png)

![practice8-branch](screenshots/practice8-branch.png)
