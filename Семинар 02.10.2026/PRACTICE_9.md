# Практика 9 — Swagger UI и GitHub Pages

## Требование и реализация

Методичка практики 9 заменяет ранний сценарий слайдов с ручным скачиванием
OpenAPI и источником Pages из ветки. Схема строится в CI через `app.openapi()`;
публикуется артефакт workflow. GitVerse заменён согласованным GitHub.

`scripts/export_openapi.py` импортирует `app.api:app`, не входит в lifespan,
не запускает Uvicorn и не обращается к HTTP. `scripts/build_api_docs.py` копирует
явный набор HTML/CSS/JS и лицензий, затем создаёт `api/openapi.json`.
Сборка отклоняет посторонние файлы в выходном каталоге без его рекурсивного удаления.

В `docs/api/` находятся локальные Swagger UI 5.33.1, `LICENSE`, `NOTICE` и
уведомления bundle. Происхождение и SHA-256 — в [SWAGGER_UI.md](../docs/SWAGGER_UI.md).
Пути к CSS, JS и `./openapi.json` относительные. Внешний validator и `Try it out`
отключены; статическая страница не делает FastAPI публичным.

## Локальная сборка

```powershell
py -3.11 -m pytest -q scripts/tests/test_export_openapi.py
py -3.11 -m scripts.export_openapi --output site/api/openapi.json
py -3.11 -m scripts.build_api_docs --output site
py -3.11 -m json.tool site/api/openapi.json > $null
py -3.11 -m http.server 8090 --bind 127.0.0.1 --directory site
```

Откройте `http://127.0.0.1:8090/api/`, раскройте `/predict` и проверьте загрузку
схемы и локальных ресурсов. Тест экспорта запрещает загрузку модели и сетевые
соединения в свежем процессе; HTTP-тест статики проверяет префикс репозитория.
Готовую схему не добавляют в Git: `site/` исключён отдельным правилом.

## CI и публикация

Workflow **Publish API documentation** запускается при PR, push в `main` и вручную.
`build` устанавливает зависимости, запускает пять экспортных/сборочных тестов,
собирает `${RUNNER_TEMP}/site`, проверяет JSON и загружает Pages artifact.
`deploy` зависит от `build` и работает только на `main` вне события PR.
Права `pages: write` и `id-token: write` выдаются только deploy;
environment — `github-pages`, исходная сборка имеет `contents: read`.

В **Settings → Pages** выберите **GitHub Actions**. Environment разрешает `main`.
Ручной запуск: **Actions → Publish API documentation → Run workflow → main**.
Ручной запуск рабочей ветки проверяет артефакт без публикации.

Опубликованные URL документации:
[Swagger UI](https://kirill-erofeev.github.io/development-and-integration-labs/api/) и
[JSON](https://kirill-erofeev.github.io/development-and-integration-labs/api/openapi.json).
HTTP `200`, загрузка схемы и локальных ресурсов, соответствие опубликованного
контракта проверенному SHA подтверждены в [CHECKS.md](CHECKS.md).

Ветка последовательной истории — `replay-20261005/lab-09-pages`, соответствующая рабочей
`feature/swagger-ui-pages` из методички. Сначала проверяется PR, затем новый run
после merge в `main`. Word-отчёт оформляется отдельно пользователем.

## Проверки и материалы сдачи

Статус: **фактический прогон выполнен**. Проверенный SHA, команды,
коды завершения, результаты и ссылки на журналы приведены в [CHECKS.md](CHECKS.md).
Команды и ожидаемые ответы выше описывают сценарий воспроизведения проверки.

Снимки фактических проверок:

- [practice9-export.png](screenshots/practice9-export.png).
- [practice9-workflow.png](screenshots/practice9-workflow.png).
- [practice9-swagger.png](screenshots/practice9-swagger.png).

Снимки доступны по указанным ссылкам и связаны с протоколом этого этапа.
Снимки фиксируют проверенный коммит; последующее добавление материалов сдачи
не должно подменять его другим состоянием кода. Старые прогоны не подтверждают этот этап.
Word-отчёт пользователь оформляет отдельно, используя эти снимки.
