import os
import json
from typing import Any, Dict, Optional
from datetime import datetime, date
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import AsyncOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# -- DIRECTORY RESOLUTION & CONFIG --
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_DIR = os.path.join(BASE_DIR, "GoogleAdsMCP") 
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
UV_BIN = "/Users/mesut/.local/bin/uv"

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

CUSTOMER_ID = config.get("google_ads_customer_id", "")

# Initialize FastAPI
app = FastAPI()

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    prompt: str

class DirectToolRequest(BaseModel):
    tool_name: str
    arguments: Optional[Dict[str, Any]] = None

# --- MCP Connection Helper ---
def get_mcp_server_params() -> StdioServerParameters:
    server_env = os.environ.copy()
    
    server_env["GOOGLE_ADS_DEVELOPER_TOKEN"] = config.get("developer_token", "")
    server_env["GOOGLE_ADS_CLIENT_ID"] = config.get("client_id", "")
    server_env["GOOGLE_ADS_CLIENT_SECRET"] = config.get("client_secret", "")
    server_env["GOOGLE_ADS_REFRESH_TOKEN"] = config.get("refresh_token", "")
    server_env["GOOGLE_ADS_LOGIN_CUSTOMER_ID"] = config.get("login_customer_id", "")
    server_env["GOOGLE_ADS_CUSTOMER_ID"] = CUSTOMER_ID

    return StdioServerParameters(
        command=UV_BIN,
        args=["run", "--directory", MCP_DIR, "google-ads-mcp"],
        cwd=MCP_DIR,
        env=server_env
    )

@app.post("/execute-tool")
async def execute_tool(request: DirectToolRequest):
    """Executes a specific MCP tool directly."""
    print("\n" + "-"*10 + "Get-All-Tools" + "-"*10 + "\n")
    print(f" direct tool request: {request.tool_name}" + "\n")
    print("-"*25 + "\n")

    tool_args = request.arguments or {}
    print(f" raw arguments: {json.dumps(tool_args, ensure_ascii=False)}")

    # Auto-inject customer_id if missing
    if "customer_id" not in tool_args and CUSTOMER_ID:
        tool_args["customer_id"] = CUSTOMER_ID
        print(f" auto-injected customer_id: {CUSTOMER_ID}")

    try:
        print(" connecting to mcp server via stdio...")
        async with stdio_client(get_mcp_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print(f" executing '{request.tool_name}'...")

                result = await session.call_tool(request.tool_name, arguments=tool_args)
                print(f" tool execution completed | isError: {getattr(result, 'isError', False)}")

                formatted_data = []
                for item in result.content:
                    text_val = getattr(item, "text", str(item))
                    try:
                        formatted_data.append(json.loads(text_val))
                    except (json.JSONDecodeError, TypeError):
                        formatted_data.append(text_val)

                print(" payload parsed successfully.")
                print("-"*50 + "\n")

                return {
                    "tool": request.tool_name,
                    "is_error": getattr(result, "isError", False),
                    "data": formatted_data
                }
    except Exception as e:
        print(f" error in execute_tool: {str(e)}")
        print("-"*50 + "\n")
        raise HTTPException(status_code=500, detail=str(e))


SYSTEM_PROMPT = (
    f"Sen uzman bir Google Ads analistisin. Bugünün tarihi {date.today().isoformat()}. "
    f"Analiz etmen gereken Google Ads Müşteri Kimliği: '{CUSTOMER_ID}'. "
    "ZORUNLU KURALLAR: "
    "1. Kullanıcı bir kampanya veya reklam grubu İSMİ verdiğinde (örn: 'Elmalı Reklam Grubu'), doğrudan bu metni ID bekleyen araçlara (tools) GİRME. "
    "2. Her zaman iki adımlı işlem yap: ÖNCE arama/sorgu aracını kullanarak bu ismin sayısal ID'sini (Resource Name veya ID) veritabanından bul. SONRA bulduğun bu sayısal ID'yi veya kaynak adını kullanarak anahtar kelimeleri/metrikleri sorgula. "
    "3. Canlı verileri sorgulamak için HER ZAMAN sana sunulan araçları kullan. "
    "4. Hata alırsan mazeret uydurma (özel karakterler vb. halüsinasyonlar yapma), farklı bir sorgu veya araç ile tekrar dene. "
    "5. Kullanıcıya asla 'bekle', 'kontrol ediyorum' veya 'zaman alacak' diyerek aracı çağırmadan yanıt verme. Gerekli tüm araçları sırayla çağırıp analizi tamamla. "
    "6. Nihai veri özetini her zaman Türkçe olarak sun. Cevabının sonuna KESİNLİKLE 'Başka bir konuda yardımcı olabilir miyim?' gibi kapanış veya takip soruları ekleme."
)

@app.post("/chat")
async def chat_with_agent(request: ChatRequest):
    """Passes user prompt to OpenAI with multi-turn iterative tool calling."""
    print("\n" + "-"*10 + "AI-Prompt" + "-"*10 + "\n")
    print(f" [AGENT] Incoming User Prompt: \"{request.prompt}\"" + "\n")
    print("-"*25 + "\n")

    openai_client = AsyncOpenAI(api_key=config.get("openai_api_key", ""))

    try:
        print("[AGENT] Initializing Google Ads MCP Server Session...")
        async with stdio_client(get_mcp_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("[AGENT] MCP Server Connected.")
                
                # 1. Fetch MCP tools
                mcp_tools = await session.list_tools()
                print(f"[AGENT] Loaded {len(mcp_tools.tools)} MCP tools into schema.")
                
                openai_tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": t.name,
                            "description": t.description,
                            "parameters": t.inputSchema
                        }
                    }
                    for t in mcp_tools.tools
                ]

                # 2. Add System Prompt + User Prompt
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": request.prompt}
                ]
                
                max_iterations = 10  # Prevents infinite loops
                iteration = 0

                while iteration < max_iterations:
                    iteration += 1
                    print(f"\n[AGENT] Iteration {iteration}: Querying OpenAI (gpt-4o)...")
                    
                    response = await openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=messages,
                        tools=openai_tools
                    )
                    
                    message = response.choices[0].message

                    # If model didn't call any tools, we have our final text answer
                    if not message.tool_calls:
                        print("[AGENT] Model finished tool execution. Generating final answer.")
                        print("#"*60 + "\n")
                        return {"response": message.content}

                    # Append model's tool calls to conversational history
                    messages.append(message)
                    print(f"[TOOL CALL] OpenAI requested {len(message.tool_calls)} tool execution(s):")

                    # Execute all tools requested in this step
                    for idx, tool_call in enumerate(message.tool_calls, start=1):
                        tool_name = tool_call.function.name
                        args = json.loads(tool_call.function.arguments)

                        if "customer_id" not in args and CUSTOMER_ID:
                            args["customer_id"] = CUSTOMER_ID

                        print(f"  [{idx}] Executing: {tool_name}")
                        print(f"      Arguments: {json.dumps(args, ensure_ascii=False)}")

                        result = await session.call_tool(tool_name, arguments=args)

                        tool_result_text = "\n".join(
                            [getattr(item, "text", str(item)) for item in result.content]
                        )

                        preview = tool_result_text[:200] + "..." if len(tool_result_text) > 200 else tool_result_text
                        print(f"      Result ({len(tool_result_text)} chars): {preview}")

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result_text
                        })

                # Fallback if max iterations exceeded
                print("[AGENT WARNING] Max tool iterations reached.")
                final_fallback = await openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )
                print("#"*60 + "\n")
                return {"response": final_fallback.choices[0].message.content}

    except Exception as e:
        print(f"[AGENT ERROR] Execution failed: {str(e)}")
        print("#"*60 + "\n")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools")
async def list_available_tools():
    """Lists all tools and parameter schemas exposed by the Google Ads MCP server."""
    print("\n" + "-"*10 + "Get-Tools" + "-"*10 + "\n")
    try:
        async with stdio_client(get_mcp_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                mcp_tools = await session.list_tools()
                print(f"--- [GET /tools] Successfully fetched {len(mcp_tools.tools)} tools ---")

                return {
                    "count": len(mcp_tools.tools),
                    "tools": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema,
                        }
                        for tool in mcp_tools.tools
                    ],
                }
    except Exception as e:
        print(f"--- [GET /tools ERROR] {str(e)} ---")
        raise HTTPException(status_code=500, detail=str(e))