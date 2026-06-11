from openai import OpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

def generate_dashboard_plan(df, user_prompt):

    columns = df.columns.tolist()
    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
    sample = df.head(5).to_string()

    prompt = f"""
You are a Project Management Dashboard Expert.

Dataset Columns:
{columns}

Column Types:
{dtypes}

Sample Data (first 5 rows):
{sample}

User Request:
{user_prompt}

Design a dashboard for this request. Return ONLY valid JSON with this exact structure:

{{
    "title": "Dashboard title based on the user request",
    "kpis": [
        {{"column": "Progress", "agg": "mean", "label": "Avg Progress"}},
        {{"column": "Days Required", "agg": "sum", "label": "Total Days"}}
    ],
    "charts": [
        {{"type": "bar", "x": "Assigned to", "y": "Days Required", "title": "Workload by Person"}},
        {{"type": "line", "x": "Start Date", "y": "Progress", "title": "Progress Over Time"}},
        {{"type": "pie", "x": "Status", "y": "Days Required", "title": "Days by Status"}},
        {{"type": "scatter", "x": "Days Required", "y": "Progress", "title": "Effort vs Progress"}}
    ],
    "table": {{
        "columns": ["Project Name", "Assigned to", "Progress"],
        "sort_by": "Progress",
        "ascending": false,
        "title": "Project Details"
    }},
    "insight": "2-3 sentence analysis answering the user's request based on the data."
}}

Rules:
- Only use column names that exist in the dataset columns list above (match exactly, case-sensitive).
- "agg" must be one of: "sum", "mean", "count", "max", "min". Use numeric columns for sum/mean/max/min.
- "type" must be one of: "bar", "line", "pie", "scatter", "histogram". For "histogram" only "x" is required.
- Include 2 to 4 KPIs and 2 to 4 charts that best answer the user's request.
- The table should show the most relevant columns for the request.
"""

    response = client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3
    )

    content = response.choices[0].message.content

    # Strip markdown code fences if the model wraps the JSON
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0]

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "title": "AI Dashboard",
            "kpis": [],
            "charts": [],
            "table": None,
            "insight": content
        }