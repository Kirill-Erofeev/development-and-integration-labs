# Протоколы проверок

Ниже сохранены протоколы фактических проверок. Незавершённые этапы обозначены отдельно. Записи ранних практик при
добавлении следующей сохраняются; старые SHA и runs из прежней истории не переносятся.

## Зачёт: вариант 4 — фактическая проверка

Проверенный коммит: `66fb85ac2b20e20b367717e4e0ce2770cd1bbb9c`. Дата: 2026-10-04T22:38:06.879312+03:00.

| Проверка | Фактический код | Результат |
| --- | --- | --- |
| Готовность модели | 0 | succeeded |
| Контрольный прогноз | 0 | succeeded |
| Ошибка валидации | 0 | succeeded |
| Паспорт модели | 0 | succeeded |
| UUID и журнал | 0 | succeeded |
| Журнал Uvicorn | 0 | succeeded |
| Notebook варианта 4 | 0 | succeeded |
| pytest | 0 | succeeded |

[Полный журнал](evidence/exam4-20261004-223806/commands.log), [манифест](evidence/exam4-20261004-223806/manifest.json).

[Новый pull request](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/20).

[Учебный саморазбор автора](https://github.com/Kirill-Erofeev/development-and-integration-labs/pull/20#issuecomment-5983701374) выполнен по согласованному исключению. Независимое ревью не заявляется. При подготовке исправлена передача UUID для HTTP 400 при некорректной UTF-8 кодировке тела; регрессионный тест входит в успешный полный прогон.

[GitHub ci для проверенного коммита PR](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/37229358498) — success.

[GitHub publish-api-docs для проверенного коммита PR](https://github.com/Kirill-Erofeev/development-and-integration-labs/actions/runs/37229358522) — success.

Контейнерная проверка того же коммита:

| Проверка | Фактический код | Результат |
| --- | --- | --- |
| Сборка API и клиента | 0 | succeeded |
| Запуск Compose | 0 | succeeded |
| Готовность API | 0 | succeeded |
| Завершение клиента | 0 | succeeded |
| Состояния сервисов | 0 | succeeded |
| Логи сервисов | 0 | succeeded |
| Результат клиента | 0 | succeeded |
| Остановка Compose | 0 | succeeded |
| Сохранность результата | 0 | succeeded |

[Журнал Compose](evidence/exam4-containers-20261004-223917/commands.log), [манифест Compose](evidence/exam4-containers-20261004-223917/manifest.json).

![Зачёт: Compose](screenshots/exam4-containers.png)

![exam4-predict](screenshots/exam4-predict.png)

![exam4-error](screenshots/exam4-error.png)

![exam4-passport](screenshots/exam4-passport.png)

![exam4-log](screenshots/exam4-log.png)

![exam4-tests](screenshots/exam4-tests.png)
