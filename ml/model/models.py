import mlflow
import pandas as pd
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
import os

from utils.db import mlflow_db_url, sql_select, sql_execute
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
    
class QualityExplanation(BaseModel):
    title: str
    message: str

ollama_model = OpenAIChatModel(
    'llama3',
    base_url=os.getenv("GEN_AI_URL"),
    api_key='ollama'
)

explainer_agent = Agent(
    ollama_model,
    result_type=QualityExplanation,
    system_prompt=(
        "You are a manufacturing QC expert. Compare the failed sample data to the "
        "baseline good data. Provide a short, technical explanation for why it failed. "
        "Classify the issue into a short title (e.g., 'Temperature Variance', 'Pressure Drop')."
    )
)

def run_explainer(sample_id):
    print(f"Running explainer for failed sample: {sample_id}...")

    bad_query = """
    SELECT f.temperature, f.pressure, f.ph_level, 
    SUM(m.intensity) as total_intensity
    FROM samples s
    JOIN fab_data f ON f.sample_id = s.id
    JOIN ms_data m ON m.sample_id = s.id
    WHERE s.id = %s
    GROUP BY f.temperature, f.pressure, f.ph_level;
    """
    bad_df = sql_select(bad_query, (sample_id, ))

    if bad_df.empty:
        print("Sample data not found")
        return
    bad_data = bad_df.iloc[0].to_dict()

    good_query = """
    SELECT AVG(f.temperature) as avg_temp, AVG(f.pressure) as avg_press, AVG(f.ph_level) as avg_ph
        FROM samples s 
        JOIN fab_data f ON f.sample_id = s.id 
        JOIN (
            SELECT sample_id, SUM(intensity) as total_intensity 
            FROM ms_data 
            GROUP BY sample_id 
            HAVING SUM(intensity) > 17000
        ) m ON m.sample_id = s.id;
    """
    good_data = sql_select(good_query).iloc[0].to_dict()

    prompt = f"Failed Sample Data: {bad_data}\nBaseline Good Data: {good_data}"
    result = explainer_agent.run_sync(prompt)
    explanation = result.data

    insert_query = """
    INSERT INTO sample_explanations (sample_id, title, message)
    VALUES (%s, %s, %s)
    """
    sql_execute(insert_query, (sample_id, explanation.title, explanation.message))

    print(f"Explanation saved - Title: {explanation.title}")

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