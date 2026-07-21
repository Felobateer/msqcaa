import mlflow
import pandas as pd

from utils.db import mlflow_db_url
from utils.raw_explainer import run_explainer
from model.train import TrainingLab

class ModelHandler:
    def __init__(self):
        mlflow.set_tracking_uri(mlflow_db_url)
        self.experiment_name = "Paracetamol_MS_Quality"

    def get_latest_model(self):
        """Fetches the most recently trained model."""
        runs = mlflow.search_runs(
            experiment_names=[self.experiment_name],
            order_by=["start_time DESC"],
            max_results=1
        )
        
        if runs.empty:
            return None
            
        run_id = runs.iloc[0].run_id
        return mlflow.pyfunc.load_model(f"runs:/{run_id}/model")

    def get_most_accurate_model(self):
        """Fetches the model with the highest F1 score."""
        runs = mlflow.search_runs(
            experiment_names=[self.experiment_name],
            order_by=["metrics.f1_score_test DESC"],
            max_results=1
        )
        
        if runs.empty:
            return None
            
        run_id = runs.iloc[0].run_id
        return mlflow.pyfunc.load_model(f"runs:/{run_id}/model")

# Explain by raw data
def run_inference(model):
    lab = TrainingLab(model.name, model.type)
    print(f"Running inference on {model.type} model: {model.name}")
    
    old_f1_score = model.f1_score
    f1_score = lab.inference_training(model.id)
    if old_f1_score < f1_score:
        print(f"Model accuracy increased by {f1_score - old_f1_score}")
    elif f1_score < old_f1_score:
        print(f"Model accuracy decreased by {old_f1_score - f1_score}")


def check_quality(model_class, data):
    handler = ModelHandler() 
    
    if model_class == "latest":
        model = handler.get_latest_model()
    elif model_class == "accurate":
        model = handler.get_most_accurate_model()
    else:
        raise ValueError("Invalid model_class. Use 'latest' or 'accurate'.")
        
    if model is None:
        raise ValueError("No models found in MLflow registry.")

    print(f"Using the {model_class} model to check compound id: {data.id}")
    
    # Isolate only the features the model expects into a 2D format
    features = pd.DataFrame([{
        'temperature': data.temperature,
        'pressure': data.pressure,
        'ph_level': data.ph_level
    }])
    
    # Return the single prediction integer (0 or 1)
    prediction = int(model.predict(features)[0])
    
    if prediction == 0:
        run_explainer(data.id)
    
    run_inference(model)

    return prediction