import mlflow
from mlflow.sklearn import log_model

from model import train_model

mlflow.set_tracking_uri("sqlite:///mlflow.db")
mlflow.set_experiment("moderation-model")

with mlflow.start_run():
    model = train_model()
    log_model(model, "model", registered_model_name="moderation-model")

client = mlflow.MlflowClient()
versions = client.search_model_versions("name='moderation-model'")
if versions:
    client.transition_model_version_stage(
        name="moderation-model",
        version=versions[0].version,
        stage="Production",
    )
