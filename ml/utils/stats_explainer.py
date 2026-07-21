import os
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage, SystemMessage

from utils.db import sql_select, sql_execute

load_dotenv()

class QualityExplanation(BaseModel):
    title: str
    message: str

# Configured for GCP Vertex AI
# Required GCP environment variables:
# GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_REGION
llm = ChatVertexAI(
    model="gemini-1.5-pro",
    temperature=0,
).with_structured_output(QualityExplanation)

def get_stats():
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
    return sql_select(good_query).iloc[0].to_dict()

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
    spc_stats = get_stats()

    system_prompt = f"""You are a process engineer that was alarmed by the ML model that this 
    sample is detected as an anomaly. 
    
    Overall SPC Data (Normal Baseline):
    {spc_stats}
    
    Using the SPC data, determine whether this is a false alarm or if the sample actually is an anomaly. 
    If it is an anomaly, provide an explanation as to why."""

    result = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Sample Data: {bad_data}")
    ])

    insert_query = """
        INSERT INTO sample_explanations (sample_id, title, message)
        VALUES (%s, %s, %s)
        """
    sql_execute(insert_query, (sample_id, result.title, result.message))

    print(f"Explanation saved - Title: {result.title}")