# Сбор доказательств выполнения

Пакет сохраняет фактические результаты явно выбранных команд в `manifest.json`
и текстовом `commands.log`, проверяет их согласованность и создаёт HTML в прежнем
стиле материалов курса. Chrome снимает HTML или настоящий интерфейс по URL
с шириной 1440 px. Импорт пакета не запускает процессы и ничего не записывает.

## Зависимости

Сбор команд, проверка манифеста и HTML работают на стандартной библиотеке Python.
Для снимков отдельно нужны установленный Chrome и зависимость из
`scripts/evidence/requirements.txt`:

```powershell
py -3.11 -m pip install -r scripts/evidence/requirements.txt
```

Пакеты приложения не меняются. Импорт `websocket` выполняется только при запуске
браузера; обычные тесты пакета Chrome не запускают.

## Последовательность

1. Выберите разрешённые команды и конкретную проверяемую версию проекта.
2. Выполните команды, сохраняя один новый каталог на прогон. Ожидаемую ошибку
   задайте явно через `expected_returncode`; она получит состояние
   `expected_failure`, а не `succeeded`.
3. Завершите прогон. Проверьте фактические результаты и требования лабораторной.
4. Сформируйте HTML из манифеста. Полный вывод остаётся в журнале; выборка строк
   обозначается на карточке.
5. Снимите HTML или настоящий интерфейс. Результат и манифест снимка сохраняются
   по указанному пути. Существующие HTML/PNG не перезаписываются.

```powershell
py -3.11 -B -m scripts.evidence collect --output .verification/evidence/example --cwd . --title "Проверка версии Python" --label "Python" -- py -3.11 --version
py -3.11 -B -m scripts.evidence validate .verification/evidence/example/manifest.json
py -3.11 -B -m scripts.evidence render .verification/evidence/example/manifest.json --output .verification/evidence/example/report.html
$reportUrl = ([System.Uri](Resolve-Path .verification/evidence/example/report.html).Path).AbsoluteUri
py -3.11 -B -m scripts.evidence capture --url $reportUrl --output .verification/evidence/example/report.png --cwd . --profile-root .verification/evidence/browser
```

CLI `collect` возвращает ненулевой код при неожиданном результате. Для нескольких
команд используйте Python API:

```python
from pathlib import Path
import sys

from scripts.evidence import EvidenceRun, render_report

with EvidenceRun(Path(".verification/evidence/python"), cwd=Path.cwd(),
                 title="Проверка окружения") as run:
    run.command("Python", [sys.executable, "--version"])
    run.command("Синтетическая ожидаемая ошибка",
                [sys.executable, "-c", "raise SystemExit(2)"], expected_returncode=2)

render_report(run.manifest_path, run.directory / "report.html")
```

Браузер может работать с настоящим Swagger или интерфейсом. Сервер должен быть
заранее запущен из нужной версии проекта. Пакет не запускает сервер за пользователя.

```python
from pathlib import Path

from scripts.evidence.browser import BrowserSession

with BrowserSession(profile_root=Path(".verification/evidence/browser")) as browser:
    browser.capture("http://127.0.0.1:8000/docs",
                    Path(".verification/evidence/swagger.png"),
                    cwd=Path.cwd(), wait_selector=".swagger-ui .opblock")
```

Для взаимодействия доступны `navigate`, `wait_for_selector`, `evaluate`,
`capture_current`, `screenshot`. После заполнения формы или раскрытия Swagger
вызовите `capture_current(destination, cwd=...)`: он сохраняет текущее состояние
без повторной навигации. Методы `capture` и `capture_current` сохраняют рядом с PNG файл `*.png.json` с URL,
временем, размером, SHA-256 изображения и состоянием Git. Метод `screenshot`
сохраняет только изображение уже открытого состояния; его происхождение следует
фиксировать вызывающему сценарию. Профиль Chrome создаётся в новом подкаталоге
явного `profile_root`; браузер скрыт и закрывается при выходе из контекста.

## Что подтверждают артефакты

Каждая запись команды содержит argv, абсолютный cwd, начало и завершение с часовым
поясом, длительность, фактический и ожидаемый код, timeout и ошибку запуска.
stdout/stderr хранятся отдельно по диапазонам UTF-8-журнала с контрольными суммами.
Некорректные байты UTF-8 заменяются с явной отметкой `utf8_lossless: false`.
Окружение процесса и его переменные в манифест не выгружаются.

Git-происхождение проверяется до и после каждой команды. `verified_sha`
присваивается только при неизменном HEAD и отсутствии изменений отслеживаемых
файлов. `tracked_clean` вычисляется через `git status --untracked-files=no`;
untracked-файлы не перечисляются и не читаются. Их наличие не означает изменения
Git-коммита, но исполняемые незакоммиченные программы нужно проверять отдельно.
SHA характеризует отслеживаемое дерево, а не все файлы диска или запущенный сервер.

Рендерер проверяет формат, время, порядок записей, Git-происхождение, диапазоны,
хеши захваченного вывода и соответствие статусов реальным кодам. Неуспешные команды
остаются видны, даже если для карточки выбрана другая часть прогона. Проверка хеша
обнаруживает случайное изменение журнала; манифест не является цифровой подписью
и не защищает от согласованной ручной подделки обоих файлов.

Для GitHub Actions команда успешного получения API-ответа сама по себе не
подтверждает успешность workflow. Отдельно проверяются run ID, `head_sha`, ветка,
заключение, jobs и steps. Дата рендеринга не заменяет дату выполнения workflow.
Доказательства проверенного коммита сохраняются следующим коммитом: добавление
снимка в проверенный коммит изменяет SHA.

Пакет не сканирует каталоги в поисках входных данных. Разрешение на конкретные
команды, их ввод/вывод и URL обеспечивает вызывающий сценарий. Защищённые таблицы,
JSONL, секреты и посторонние пользовательские материалы в команды не включаются.

## Проверка пакета

```powershell
py -3.11 -B -m pytest -q tests/test_evidence_tools.py -p no:cacheprovider
```

Тесты используют синтетические команды и данные. Они проверяют сохранение ошибок,
экранирование HTML, обнаружение повреждённого вывода и неверного происхождения.
