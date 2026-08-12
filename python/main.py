import datetime
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.ads.googleads.client import GoogleAdsClient
from openai import OpenAI

app = FastAPI()

# ------------------------ CONFIG & CLIENTS ----------------------------
with open("config.json", "r") as f:
    config = json.load(f)

OPENAI_API_KEY = config["openai_api_key"]
CUSTOMER_ID = config["google_ads_customer_id"]

# Initialize SDK clients once globally
google_ads_client = GoogleAdsClient.load_from_storage(path="google-ads.yaml")
openai_client = OpenAI(api_key=OPENAI_API_KEY)
# ------------------------ CONFIG & CLIENTS ----------------------------


class ChatRequest(BaseModel):
    user_prompt: str


# ------------------------ DATE VALIDATION ----------------------------
def validate_iso_date(date_str: str) -> str:
    """Validates and returns a clean YYYY-MM-DD string or raises ValueError."""
    try:
        parsed_date = datetime.date.fromisoformat(str(date_str).strip())
        return parsed_date.isoformat()
    except (ValueError, TypeError):
        raise ValueError(f"Invalid date format provided: {date_str}. Expected YYYY-MM-DD.")
# ------------------------ DATE VALIDATION ----------------------------


# ------------------------ GOOGLE ADS LOGIC ----------------------------
def fetch_ads_data(start_date: str, end_date: str) -> str:
    try:
        validated_start = validate_iso_date(start_date)
        validated_end = validate_iso_date(end_date)
    except ValueError as err:
        return json.dumps({"error": str(err)})
    
    ga_service = google_ads_client.get_service("GoogleAdsService")

    query = f"""
        SELECT
          campaign.id,
          campaign.name,
          segments.date,
          metrics.impressions,
          metrics.clicks,
          metrics.cost_micros,
          metrics.conversions
        FROM campaign
        WHERE segments.date BETWEEN '{validated_start}' AND '{validated_end}'
        ORDER BY segments.date ASC, campaign.id ASC
    """

    stream = ga_service.search_stream(customer_id=CUSTOMER_ID, query=query)
    all_records = []

    for batch in stream:
        for row in batch.results:
            cost = row.metrics.cost_micros / 1_000_000
            all_records.append({
                "date": row.segments.date,
                "campaign_id": row.campaign.id,
                "campaign_name": row.campaign.name,
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "cost": round(cost, 2),
                "conversions": row.metrics.conversions
            })

    if not all_records:
        return json.dumps({"message": "No data found for this date range."})

    return json.dumps(all_records)
# ------------------------ GOOGLE ADS LOGIC ----------------------------


# ------------------------ GPT TOOLS CONFIG ----------------------------
tools = [{
    "type": "function",
    "function": {
        "name": "fetch_ads_data",
        "description": "Fetches Google Ads performance data for a specific date range.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["start_date", "end_date"],
        },
    }
}]
# ------------------------ GPT TOOLS CONFIG ----------------------------


# ------------------------ FASTAPI ENDPOINTS ----------------------------
@app.post("/analyze-ads")
def analyze_ads(request: ChatRequest):
    today_str = datetime.date.today().isoformat()
    messages = [
        {"role": "system", "content": f"You are a marketing analyst. Use tools to fetch ad data before answering. Today is {today_str}."},
        {"role": "user", "content": request.user_prompt}
    ]

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        response_message = response.choices[0].message

        if response_message.tool_calls:
            messages.append(response_message)
            for tool_call in response_message.tool_calls:
                if tool_call.function.name == "fetch_ads_data":
                    args = json.loads(tool_call.function.arguments)
                    ads_data = fetch_ads_data(args.get("start_date"), args.get("end_date"))
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": "fetch_ads_data",
                        "content": ads_data,
                    })

            final_response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages
            )
            return {"response": final_response.choices[0].message.content}
        else:
            return {"response": response_message.content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test-pull")
def test_pull(request: ChatRequest):
    try:
        raw_data_string = fetch_ads_data(start_date="2026-07-01", end_date="2026-08-12")
        data_json = json.loads(raw_data_string)
        return {"response": data_json}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# ------------------------ FASTAPI ENDPOINTS ----------------------------