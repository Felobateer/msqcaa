import pandas as pd
from sklearn.model_selection import train_test_split
import lightgbm as lgb
from sklearn.neural_network import MLPClassifier as mlpc
from sklearn.preprocessing import StandardScaler as ss
from sklearn.metrics import f1_score
from sklearn.pipeline import Pipeline
import mlflow
from typing import Literal

from utils.db import sql_select, mlflow_db_url

ModelType = Literal["decision tree", "neural network learning"]

class TrainingLab():
    def __init__(self, model_name: str, model_type: ModelType):
        self.model_name = model_name
        self.model_type = model_type
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None

    def populate_data(self):
        query = """SELECT s.*,
        f.timestamp, f.temperature, f.pressure, f.ph_level,
        m.mass_to_charge, m.charge, m.intensity
        FROM samples s 
        JOIN fab_data f ON f.sample_id = s.id 
        JOIN ms_data m ON m.sample_id = s.id 
        ORDER BY s.analysis_date;"""

        data = sql_select(query)

        peak_sums = data.groupby('id')['intensity'].sum().reset_index()
        peak_sums['is_good'] = (peak_sums['intensity'] > 17000).astype(int)
        fab_features = data[['id', 'temperature', 'pressure', 'ph_level']].drop_duplicates()
        ml_df = pd.merge(fab_features, peak_sums[['id', 'is_good']], on='id').drop(columns=['id'])

        X = ml_df[['temperature', 'pressure', 'ph_level']]
        y = ml_df['is_good']

        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    def train_model(self):
        mlflow.set_tracking_uri(mlflow_db_url)
        mlflow.set_experiment("Paracetamol_MS_Quality")

        if self.model_type == "decision tree":
            mlflow.lightgbm.autolog()
            with mlflow.start_run(run_name=self.model_name):
                lgb_model = lgb.LGBMClassifier(random_state=42)
                lgb_model.fit(self.X_train, self.y_train)  # Fixed X_test to y_train
                
                lgb_preds = lgb_model.predict(self.X_test)
                lgb_score = f1_score(self.y_test, lgb_preds)
                mlflow.log_metric("f1_score_test", lgb_score)
                return lgb_score
                
        elif self.model_type == "neural network learning":
            mlflow.sklearn.autolog()
            with mlflow.start_run(run_name=self.model_name):
                # 1. Bundle the scaler and model into one Pipeline object
                pipe = Pipeline([
                    ('scaler', ss()),
                    ('nn', mlpc(random_state=42, max_iter=500))
                ])
                
                # 2. Fit the pipeline directly on the raw, unscaled data
                pipe.fit(self.X_train, self.y_train)
                
                nn_preds = pipe.predict(self.X_test)
                nn_score = f1_score(self.y_test, nn_preds)
                mlflow.log_metric("f1_score_test", nn_score)
                return nn_score

    def inference_training(self, previous_run_id: str):
        """Loads a previous model from MLflow and continues training on new data."""
        mlflow.set_tracking_uri(mlflow_db_url)
        mlflow.set_experiment("Paracetamol_MS_Quality")
        
        # 1. Fetch the exact training timestamp of the old model
        run = mlflow.get_run(previous_run_id)
        last_training_time = pd.to_datetime(run.info.start_time, unit='ms')

        # 2. Query only samples analyzed after that timestamp
        query = """SELECT s.*,
        f.timestamp, f.temperature, f.pressure, f.ph_level,
        m.mass_to_charge, m.charge, m.intensity
        FROM samples s 
        JOIN fab_data f ON f.sample_id = s.id 
        JOIN ms_data m ON m.sample_id = s.id 
        WHERE s.analysis_date > %s
        ORDER BY s.analysis_date;"""

        data = sql_select(query, (last_training_time,))

        if data.empty:
            print("No new samples found since last training.")
            return None

        # 3. Process the new batch
        peak_sums = data.groupby('id')['intensity'].sum().reset_index()
        peak_sums['is_good'] = (peak_sums['intensity'] > 17000).astype(int)
        
        batch_size = len(peak_sums)
        if batch_size < 15:
            print(f"Batch too small. Found {batch_size} samples. 15 required.")
            return None

        print(f"Sufficient batch found: {batch_size} samples. Starting training...")

        fab_features = data[['id', 'temperature', 'pressure', 'ph_level']].drop_duplicates()
        ml_df = pd.merge(fab_features, peak_sums[['id', 'is_good']], on='id').drop(columns=['id'])

        X_new = ml_df[['temperature', 'pressure', 'ph_level']]
        y_new = ml_df['is_good']

        # Split the new batch for validation (Note: test_size will be very small)
        X_train_new, X_test_new, y_train_new, y_test_new = train_test_split(
            X_new, y_new, test_size=0.2, random_state=42
        )

        run_name = f"{self.model_name}_retrained"

        if self.model_type == "decision tree":
            old_model = mlflow.lightgbm.load_model(f"runs:/{previous_run_id}/model")
            mlflow.lightgbm.autolog()
            with mlflow.start_run(run_name=run_name):
                lgb_model = lgb.LGBMClassifier(random_state=42)
                lgb_model.fit(X_train_new, y_train_new, init_model=old_model)
                
                lgb_preds = lgb_model.predict(X_test_new)
                score = f1_score(y_test_new, lgb_preds)
                mlflow.log_metric("f1_score_test", score)
                return score
                
        elif self.model_type == "neural network learning":
            old_pipe = mlflow.sklearn.load_model(f"runs:/{previous_run_id}/model")
            mlflow.sklearn.autolog()
            with mlflow.start_run(run_name=run_name):
                old_pipe.set_params(nn__warm_start=True, nn__max_iter=500)
                old_pipe.fit(X_train_new, y_train_new)
                
                nn_preds = old_pipe.predict(X_test_new)
                score = f1_score(y_test_new, nn_preds)
                mlflow.log_metric("f1_score_test", score)
                return score