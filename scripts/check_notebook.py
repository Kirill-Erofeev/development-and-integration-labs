import argparse
from contextlib import chdir
from hashlib import sha256
import json
import math
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
REVIEWED_CELL_HASHES = (
    "ebe2261a679d6809648579d35821193ba5b42045b60903630be5355ada229935",
    "003bb721f2a81091c83e1361ac20811d9ccb8556f0028c9c40d1f6e26d7bd6f0",
    "ab1cbbebc28ce224709e08a811ebc0a890cb961020fde71f18fd0d5312da141e",
    "7ea09c3a26a26e26fa3d10393bac45548debf60d3ed27df46ba90d94020d35ec",
    "ad8824624763f6b702067551c8dbf96a2f737c02edbbd9f532bcfcb02d15d314",
)
EXPECTED_ACCURACY = 0.9473684210526315


def physical_path(path: Path) -> Path:
    """Reject symbolic links and Windows reparse points before accessing file content."""
    absolute = path.absolute()
    for entry in (absolute, *absolute.parents):
        try:
            metadata = entry.lstat()
        except FileNotFoundError:
            continue
        if entry.is_symlink() or getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"Ссылки и reparse points не поддерживаются: {entry}")
    return absolute.resolve()


def reviewed_cells(notebook: Path) -> list[str]:
    """Accept exactly the five previously reviewed source cells, not arbitrary notebooks."""
    document = json.loads(notebook.read_text(encoding="utf-8"))
    cells = [
        "".join(cell["source"]).replace("\r\n", "\n").strip()
        for cell in document["cells"] if cell["cell_type"] == "code"
    ]
    hashes = tuple(sha256(source.encode("utf-8")).hexdigest() for source in cells)
    if hashes != REVIEWED_CELL_HASHES:
        raise ValueError("Ожидались ровно пять проверенных ячеек source_experiment.ipynb")
    return cells


def compare_reference(namespace: dict, reference_path: Path) -> None:
    """Compare the notebook estimator with an explicitly trusted project artifact."""
    import numpy as np

    reference = namespace["joblib"].load(reference_path)
    if not isinstance(reference, dict) or set(reference) != {
        "model", "feature_columns", "target_names",
    }:
        raise ValueError("Эталон должен быть артефактом проекта с моделью и метаданными")
    if reference["feature_columns"] != namespace["feature_columns"]:
        raise AssertionError("Порядок признаков не совпал с эталоном")
    if list(reference["target_names"]) != list(namespace["iris"].target_names):
        raise AssertionError("Имена классов не совпали с эталоном")
    actual = namespace["model"]
    expected = reference["model"]
    if type(actual) is not type(expected):
        raise AssertionError("Тип модели не совпал с эталоном")
    for attribute in ("coef_", "intercept_", "classes_"):
        np.testing.assert_array_equal(
            getattr(actual, attribute), getattr(expected, attribute),
            err_msg=f"Не совпало поле модели {attribute}",
        )
    if actual.n_features_in_ != expected.n_features_in_:
        raise AssertionError("Число признаков не совпало с эталоном")
    print("Эталон: коэффициенты, intercept, классы и метаданные совпали точно")


def check_notebook(
    notebook: Path, input_path: Path, work_dir: Path, reference_model: Path | None = None,
) -> None:
    """Execute trusted cells in a new verification directory without changing source data."""
    notebook = physical_path(notebook)
    input_path = physical_path(input_path)
    work_dir = physical_path(work_dir)
    if not notebook.is_relative_to(ROOT) or notebook.name != "source_experiment.ipynb":
        raise ValueError("Notebook должен быть source_experiment.ipynb внутри репозитория")
    if input_path != ROOT / "data_sample" / "sample.csv":
        raise ValueError("Разрешён только исходный data_sample/sample.csv этого репозитория")
    verification = ROOT / ".verification"
    if work_dir == verification or not work_dir.is_relative_to(verification):
        raise ValueError("Рабочий каталог должен быть вложен в .verification этого репозитория")
    if work_dir.exists():
        raise ValueError("Рабочий каталог уже существует; выберите новый, файлы не перезаписываются")
    if not input_path.is_file():
        raise ValueError("Отсутствует разрешённый data_sample/sample.csv")
    if reference_model is not None:
        reference_model = physical_path(reference_model)
        if reference_model != ROOT / "models" / "model.pkl" or not reference_model.is_file():
            raise ValueError("Эталон должен быть существующим models/model.pkl этого репозитория")

    cells = reviewed_cells(notebook)
    compiled = [compile(source, f"{notebook.name}:cell_{index}", "exec")
                for index, source in enumerate(cells, 1)]
    # Exclusive creation keeps prior verification data and the source CSV untouched.
    work_dir.mkdir(parents=True, exist_ok=False)
    with input_path.open("rb") as source, (work_dir / "sample.csv").open("xb") as target:
        shutil.copyfileobj(source, target)

    namespace = {"__name__": "__main__"}
    with chdir(work_dir):
        for index, code in enumerate(compiled, 1):
            print(f"Ячейка {index}/5", flush=True)
            exec(code, namespace)

    accuracy = float(namespace["accuracy_score"](namespace["y_test"], namespace["y_pred"]))
    if not math.isclose(accuracy, EXPECTED_ACCURACY, rel_tol=0, abs_tol=1e-15):
        raise AssertionError(f"Неожиданная accuracy: {accuracy!r}")
    if namespace["predicted_class"] != 0 or namespace["predicted_name"] != "setosa":
        raise AssertionError("Ожидалось предсказание класса 0 (setosa)")
    if not (work_dir / "model.pkl").is_file():
        raise AssertionError("Notebook не сохранил model.pkl")
    if reference_model is not None:
        compare_reference(namespace, reference_model)
    print(f"Проверка пройдена: accuracy={accuracy!r}; класс=0; имя=setosa")
    print(f"Артефакт notebook: {work_dir / 'model.pkl'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Выполнить пять доверенных ячеек исходного Iris-notebook в новом каталоге",
    )
    parser.add_argument("--notebook", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--reference-model", type=Path)
    args = parser.parse_args(argv)
    try:
        check_notebook(args.notebook, args.input, args.work_dir, args.reference_model)
    except (OSError, ValueError, KeyError, TypeError, AssertionError, ImportError) as exc:
        print(f"Проверка notebook не пройдена: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
