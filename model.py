import os
import pickle
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression


def train_model():
    np.random.seed(42)
    X = np.random.rand(1000, 4)
    y = (X[:, 0] < 0.3) & (X[:, 1] < 0.2)
    y = y.astype(int)

    model = LogisticRegression()
    model.fit(X, y)
    return model


def save_model(model, path: str = "model.pkl") -> None:
    with open(path, "wb") as f:
        pickle.dump(model, f)


def load_model(path: str = "model.pkl"):
    with open(path, "rb") as f:
        return pickle.load(f)


def load_model_from_mlflow(model_name: str = "moderation-model", stage: str = "Production"):
    import mlflow
    model_uri = f"models:/{model_name}/{stage}"
    return mlflow.sklearn.load_model(model_uri)


def ensure_model(path: str = "model.pkl"):
    p = Path(path)
    if p.exists():
        return load_model(path)
    model = train_model()
    save_model(model, path)
    return model


def get_model():
    use_mlflow = os.environ.get("USE_MLFLOW", "").lower() == "true"
    if use_mlflow:
        return load_model_from_mlflow()
    return ensure_model(path=os.environ.get("MODEL_PATH", "model.pkl"))
