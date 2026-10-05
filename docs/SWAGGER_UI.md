# Локальные файлы Swagger UI

Версия: **5.33.1**, релиз от 01.10.2026; источник проверен 04.10.2026.
Commit upstream: `cac3d136b5e37bfbe3288c8591f6f4fcf9870599`.

Файлы загружены без изменений из официального репозитория
[`swagger-api/swagger-ui`](https://github.com/swagger-api/swagger-ui/tree/cac3d136b5e37bfbe3288c8591f6f4fcf9870599).
[Страница релиза](https://github.com/swagger-api/swagger-ui/releases/tag/v5.33.1).

| Локальный файл в `docs/api/` | Исходный путь | SHA-256 |
| --- | --- | --- |
| `swagger-ui.css` | `dist/swagger-ui.css` | `1ac324f7dcd27e4b9386b4bd6421271ec147e922a22c05ba24b11515e9aa6321` |
| `swagger-ui-bundle.js` | `dist/swagger-ui-bundle.js` | `050bc415ee7048dcd881682678f720264e7da5e373f7461d7c58c755305255f7` |
| `swagger-ui-bundle.js.LICENSE.txt` | `dist/swagger-ui-bundle.js.LICENSE.txt` | `63818894e4b04cd0e3180d9cb20761e227a939121e7484f8e1d528227c756f89` |
| `LICENSE` | `LICENSE` | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` |
| `NOTICE` | `NOTICE` | `0d20d1adef18aee3f40dd258172155521ce702ac445cb5f7b7d60ed32dad2fb2` |

Страница использует стандартный `BaseLayout`: отдельный standalone preset не нужен.
Минимальный комплект CSS и bundle соответствует
[инструкции FastAPI о локальных ресурсах документации](https://fastapi.tiangolo.com/how-to/custom-docs-ui-assets/#download-the-files).
Исходные карты `.map` не включены: они нужны отладчику, а не отображению Swagger UI.
Ссылка на карту в неизменённом CSS может дать 404 при открытии соответствующего инструмента DevTools.

Исходные `LICENSE`, `NOTICE` и уведомления о компонентах bundle сохранены рядом с JS
и копируются в артефакт сайта. Сгенерированные upstream-файлы не переводились и не редактировались.
Это фиксация поставляемых upstream уведомлений, а не самостоятельный аудит лицензий всех зависимостей.

`index.html` — собственная страница проекта. Она загружает CSS, JS и схему относительными URL;
CDN не используется. `validatorUrl: null` отключает внешний валидатор, а
`supportedSubmitMethods: []` отключает отправку запросов с сайта документации.
Параметры сверены с
[официальной конфигурацией Swagger UI](https://swagger.io/docs/open-source-tools/swagger-ui/usage/configuration/).
