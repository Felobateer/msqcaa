import os
from sqlalchemy import create_engine, text
import pandas as pd
import pickle
import psycopg2

psy_url = os.getenv("DB_URL")
db_url = psy_url.replace("postgres://", "postgresql+psycopg2://")
mlflow_db_url = psy_url.replace("postgres://", "postgresql://")
engine = create_engine(db_url)


def sql_select(query: str) -> pd.DataFrame:
    print(f"quering {query}")
    return pd.read_sql(query, engine)

def sql_execute(query: str, params: tuple | dict | None = None) -> bool:
    print(f"executing: {query} \n with params {params}")
    conn = psycopg2.connect(psy_url)
    cursor = conn.cursor()
    if params:
        cursor.execute(query, params) 
    else:
        cursor.execute(query)
    
    conn.commit()
    print("Query executed successfully")
    cursor.close()
    conn.close()
    return True

def load_models(name: str): 
    query = text("SELECT model_binary FROM models WHERE name = :name LIMIT 1;")

    with engine.connect() as conn:
        result = conn.execute(query, {"name": name}).fetchone()
    
    if not result:
        raise ValueError(f"No model found with name: {name}")
    
    model = pickle.loads(result[0])
    return model