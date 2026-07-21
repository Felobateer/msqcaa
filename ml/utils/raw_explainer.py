from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
import os

from utils.db import sql_select, sql_execute

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
