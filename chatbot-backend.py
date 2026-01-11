import boto3
import pg8000
import json

# =========================
# RDS CONFIG
# =========================
RDS_HOST = "rds"
RDS_DB = "postgres"
RDS_USER = "postgres"
RDS_PASS = ""
RDS_PORT = 5432

# =========================
# AWS CLIENT
# =========================
bedrock = boto3.client("bedrock-runtime", region_name="us-west-2")

# =========================
# VIEW & FILTER PROMPT
# =========================
NL_TO_VIEW_PROMPT = """
You are a data assistant for a financial analytics system.

Your task:
1. Identify the user's intent
2. Select exactly ONE database view from the list below
3. Use ONLY column names that exist in the selected view
4. Output ONLY valid JSON
5. Provide a short, human-friendly answer summary based on the view (optional) after the JSON

IMPORTANT:
- Use English sector names for filtering
- Do not use Arabic for filters
- Use `department_name` only when the question mentions a department
- If a view has `sector`, do NOT use `sector_description` as a filter

Available views and columns:
1. v_projects_with_remaining_budget
   - project_number, project_name, department_name, sector, sector_description, final_amount, invoiced_amount, remaining_amount

2. v_variance_by_department
   - department_name, projects_count, total_budget, total_final_amount, avg_variance

3. v_budget_by_sector
   - sector, sector_description, total_projects, total_budget, total_final_amount, total_invoiced, total_remaining

4. v_budget_by_sector_department
   - sector, sector_description, department_name, total_projects, total_budget, total_final_amount, total_remaining

5. v_unlinked_projects
   - project_number, project_name, department_name, sector, sector_description, budget, final_amount, variance_status

6. v_procurement_activity_by_sector
   - sector, sector_description, open_prs, total_pos, closed_pos

Return JSON only:
{
  "view": "<view_name>",
  "filters": {
  }
}
"""

# =========================
# MAPPINGS
# =========================
SECTOR_MAP = {
    "Board": "BOD",
    "Assets": "AMS",
    "Development": "DEV",
    "Corporate Services": "FAS",
    "Government": "GOV",
    "Banks": "MSA",
    "Strategy": "PDS",
    "Endowment Planning": "PRF",
    "Regulatory Affairs": "RCS",
    "Services": "SSS",
}

DEPARTMENT_MAP = {
    "board": "مجلس الإدارة",
    "internal audit": "المراجعة الداخلية",
    "governor office": "مكتب المحافظ",
    "legal": "الشؤون القانونية",
    "finance": "الشؤون المالية",
    "it": "تقنية المعلومات",
    "hr": "الموارد البشرية",
}


# =========================
# CHATBOT FUNCTION
# =========================
def ask_chatbot(user_question: str):
    # 1. Claude prompt
    prompt = NL_TO_VIEW_PROMPT + "\n\nUser question:\n" + user_question

    response = bedrock.invoke_model(
        modelId="anthropic.claude-3-haiku-20240307-v1:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 400,
            "messages": [{"role": "user", "content": prompt}]
        })
    )

    response_body = json.loads(response["body"].read())
    claude_text = response_body["content"][0]["text"]

    # 2. Extract JSON
    try:
        view_json = json.loads(claude_text)
    except:
        return {"error": "Claude returned invalid JSON", "raw": claude_text}

    # 3. Build SQL
    view_name = view_json.get("view")
    filters = view_json.get("filters", {})

    sql = f"SELECT * FROM {view_name}"
    params = []

    if filters:
        clauses = []
        for col, val in filters.items():
            val_clean = val.strip() if isinstance(val, str) else val
            if col == "sector":
                val_clean = SECTOR_MAP.get(val_clean, val_clean)
            if col == "department_name":
                val_clean = DEPARTMENT_MAP.get(val_clean.lower(), val_clean)
            clauses.append(f"{col} = %s")
            params.append(val_clean)
        sql += " WHERE " + " AND ".join(clauses)

    # 4. Execute SQL
    conn = pg8000.connect(
        host=RDS_HOST, database=RDS_DB, user=RDS_USER, password=RDS_PASS, port=RDS_PORT
    )
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()

    # 5. Format results
    results = [dict(zip(columns, row)) for row in rows]

    # 6. Polished answer summary
    if results:
        summary = f"Found {len(results)} record(s) from {view_name}."
    else:
        summary = "No records found for your query."

    return {
        "view_json": view_json,
        "sql": sql,
        "params": params,
        "results": results,
        "summary": summary
    }

