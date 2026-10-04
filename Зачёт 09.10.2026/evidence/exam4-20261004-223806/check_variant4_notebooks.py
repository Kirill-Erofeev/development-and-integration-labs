"""Execute only the audited variant 4 notebooks against an existing trusted model."""

import argparse
from contextlib import chdir
from hashlib import sha256
import json
from pathlib import Path
import sys
from unittest.mock import patch
from uuid import UUID


WORK_ROOT = Path(__file__).resolve().parent
REVIEWED_HASHES = {
    "source_experiment_updated.ipynb": (
        "a128dcd2f88814a7b730cbc0407ec68fbff4d2cde668d36a08d6929cb31e3b46",
        "1da5c0f890a6df19f03a9a26c3dff0c767d2c28651184a826f9a41222a6379da",
    ),
    "new_functionality.ipynb": (
        "64fdcc48272f899867728ac73bfa1ffde36ed9252140223bd726c7a48685f53b",
        "178574e91396492eed76fef03d6b68d9b8f8eed7b2b644ddabe6e5b8d7d73313",
    ),
}


def physical_path(path: Path) -> Path:
    """Reject aliases before reading the notebook, model, or imported project modules."""
    absolute = path.absolute()
    for entry in (absolute, *absolute.parents):
        metadata = entry.lstat()
        if entry.is_symlink() or getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise ValueError("Ссылки и reparse points не допускаются")
    return absolute.resolve(strict=True)


def project_path(value: Path) -> Path:
    project = physical_path(value)
    allowed = {WORK_ROOT / "exam-draft", WORK_ROOT / "history-draft"}
    if project not in allowed or not project.is_dir():
        raise ValueError("Разрешены только exam-draft и history-draft этого проверочного прогона")
    for name in ("__init__.py", "common.py", "model_service.py", "request_id.py"):
        physical_path(project / "src" / name)
    for name, module in tuple(sys.modules.items()):
        if name == "src" or name.startswith("src."):
            location = getattr(module, "__file__", None)
            if not location or not Path(location).resolve().is_relative_to(project / "src"):
                raise ValueError("В процессе уже импортирован src другого проекта")
    return project


def reviewed_cells(project: Path, name: str) -> list[str]:
    if name not in REVIEWED_HASHES:
        raise ValueError("Notebook отсутствует в точном списке проверенных файлов")
    path = physical_path(project / "notebooks" / "variant4" / name)
    notebook = json.loads(path.read_text(encoding="utf-8"))
    cells = [
        "".join(cell["source"]).replace("\r\n", "\n").strip()
        for cell in notebook["cells"] if cell["cell_type"] == "code"
    ]
    hashes = tuple(sha256(source.encode("utf-8")).hexdigest() for source in cells)
    if hashes != REVIEWED_HASHES[name]:
        raise ValueError(f"Кодовые ячейки {name} отличаются от адресно проверенного варианта")
    return cells


def check(project: Path) -> None:
    project = project_path(project)
    sources = {name: reviewed_cells(project, name) for name in REVIEWED_HASHES}
    compiled = {
        name: [compile(source, f"{name}:cell_{index}", "exec")
               for index, source in enumerate(cells, 1)]
        for name, cells in sources.items()
    }
    model_path = physical_path(project / "models" / "model.pkl")
    original_model_hash = sha256(model_path.read_bytes()).hexdigest()

    import joblib
    from sklearn.linear_model import LogisticRegression

    sys.path.insert(0, str(project))
    namespaces = {}
    with chdir(project), \
         patch.object(LogisticRegression, "fit", side_effect=AssertionError("Обучение запрещено")) as fit, \
         patch("joblib.dump", side_effect=AssertionError("Сохранение модели запрещено")) as dump, \
         patch("joblib.load", wraps=joblib.load) as load:
        for name, cells in compiled.items():
            namespace = {"__name__": "__main__"}
            for code in cells:
                exec(code, namespace)
            namespaces[name] = namespace
            print(f"{name}: выполнены {len(cells)} проверенные кодовые ячейки")

        source = namespaces["source_experiment_updated.ipynb"]
        correlation = namespaces["new_functionality.ipynb"]
        assert source["project_root"] == correlation["project_root"] == project
        for name in ("src.model_service", "src.request_id"):
            assert physical_path(Path(sys.modules[name].__file__)).is_relative_to(project / "src")
        prediction = source["service"].predict([[5.1, 3.5, 1.4, 0.2]])
        assert prediction == [{"predicted_class": 0, "predicted_name": "setosa"}]
        request_id = correlation["new_id"]
        assert UUID(request_id).version == 4 and str(UUID(request_id)) == request_id
        event = correlation["prediction_event"](request_id, "setosa")
        assert event == {
            "event": "prediction_completed", "request_id": request_id, "class_name": "setosa",
        }
        load.assert_called_once_with(model_path)
        fit.assert_not_called()
        dump.assert_not_called()

    assert sha256(model_path.read_bytes()).hexdigest() == original_model_hash, "Артефакт модели изменился"
    print("Паспорт: " + json.dumps(source["passport"], ensure_ascii=False, sort_keys=True))
    print("Контрольный прогноз готовой модели: " + json.dumps(prediction, ensure_ascii=False))
    print("Событие notebook: " + json.dumps(event, ensure_ascii=False, sort_keys=True))
    print("Хеши четырёх ячеек совпали; load=1, fit=0, dump=0; models/model.pkl не изменён")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Выполнить два проверенных notebook варианта 4 без обучения")
    parser.add_argument("--projectpath", "--project-path", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        check(args.projectpath)
    except (AssertionError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Проверка notebook не пройдена: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
