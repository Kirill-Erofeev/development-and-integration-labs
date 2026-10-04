from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "model.pkl"
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data_sample" / "sample.csv"
FEATURE_COLUMNS = ("sepal_length", "sepal_width", "petal_length", "petal_width")
