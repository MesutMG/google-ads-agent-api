import os
import json
import shutil
from typing import Any, Dict, Optional
from datetime import datetime, date
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import AsyncOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# -- DIRECTORY RESOLUTION & CONFIG --
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_DIR = os.path.join(BASE_DIR, "GoogleAdsMCP") 
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
UV_BIN = shutil.which("uv") or "uv"

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

CUSTOMER_ID = config.get("google_ads_customer_id", "")

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

# --- GLOBAL PERSISTENT CONNECTION ---
mcp_stack = AsyncExitStack()
mcp_session: Optional[ClientSession] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Boots the MCP server once when FastAPI starts and keeps it alive."""
    global mcp_session
    print("\n[SYSTEM] Booting up persistent Google Ads MCP Server process...")
    try:
        read, write = await mcp_stack.enter_async_context(stdio_client(get_mcp_server_params()))
        mcp_session = await mcp_stack.enter_async_context(ClientSession(read, write))
        await mcp_session.initialize()
        print("[SYSTEM] MCP Server is running and ready for instant requests!\n")
        yield
    finally:
        print("\n[SYSTEM] Shutting down MCP Server...")
        await mcp_stack.aclose()

# Initialize FastAPI with the persistent lifespan
app = FastAPI(lifespan=lifespan)

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    prompt: str

class DirectToolRequest(BaseModel):
    tool_name: str
    arguments: Optional[Dict[str, Any]] = None


@app.post("/execute-tool")
async def execute_tool(request: DirectToolRequest):
    """Executes a specific MCP tool instantly using the persistent connection."""
    tool_args = request.arguments or {}
    
    if "customer_id" not in tool_args and CUSTOMER_ID:
        tool_args["customer_id"] = CUSTOMER_ID

    try:
        # Use the globally kept-alive session!
        result = await mcp_session.call_tool(request.tool_name, arguments=tool_args)

        formatted_data = []
        for item in result.content:
            text_val = getattr(item, "text", str(item))
            try:
                formatted_data.append(json.loads(text_val))
            except (json.JSONDecodeError, TypeError):
                formatted_data.append(text_val)

        return {
            "tool": request.tool_name,
            "is_error": getattr(result, "isError", False),
            "data": formatted_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


SYSTEM_PROMPT = (
    f"Sen uzman bir Google Ads analistisin. Bugünün tarihi {date.today().isoformat()}. "
    f"Analiz etmen gereken Google Ads Müşteri Kimliği: '{CUSTOMER_ID}'. "
    "ZORUNLU KURALLAR: "
    "1. Kullanıcı bir kampanya veya reklam grubu İSMİ verdiğinde, doğrudan bu metni ID bekleyen araçlara GİRME. "
    "2. Her zaman iki adımlı işlem yap: ÖNCE arama aracıyla sayısal ID'yi bul, SONRA bu ID ile metrikleri sorgula. "
    "3. Canlı verileri sorgulamak için HER ZAMAN sana sunulan araçları kullan. "
    "4. Hata alırsan mazeret uydurma, farklı bir sorgu veya araç ile tekrar dene. "
    "5. Kullanıcıya asla 'bekle' veya 'kontrol ediyorum' diyerek aracı çağırmadan yanıt verme. Gerekli tüm araçları sırayla çağırıp analizi tamamla. "
    "6. GENEL BİLGİ VERMEK YASAKTIR: Kullanıcı tahmin, öngörü veya strateji istediğinde (örn: 'önümüzdeki 1 yıl için tahmin yap'), ASLA sektör trendleri, yapay zeka veya gizlilik gibi jenerik makaleler yazma. Mutlaka hesabın geçmiş performans verilerini araçlarla çek ve YALNIZCA bu spesifik verilere dayanarak matematiksel bir tahmin yap. Veri yoksa tahmin yapamayacağını belirt. "
    "7. PARA BİRİMİ VE MİKROS: API'den gelen bütçe, maliyet veya harcama verileri 'micros' cinsindendir. Bu değerleri her zaman 1.000.000'a bölerek normal birime çevir. Tüm parasal değerleri SADECE Türk Lirası (TL) formatında göster. ASLA Dolar ($) sembolü veya başka bir para birimi kullanma. Micros olarak da yazma."
    "8. Nihai veri özetini her zaman Türkçe olarak sun. Cevabının sonuna KESİNLİKLE kapanış veya takip soruları ekleme."
)

@app.post("/chat")
async def chat_with_agent(request: ChatRequest):
    """Passes user prompt to OpenAI with multi-turn iterative tool calling."""
    openai_client = AsyncOpenAI(api_key=config.get("openai_api_key", ""))

    try:
        # Instantly fetch tools using the live session
        mcp_tools = await mcp_session.list_tools()
        
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

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": request.prompt}
        ]
        
        max_iterations = 8  
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            response = await openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=openai_tools
            )
            
            message = response.choices[0].message

            if not message.tool_calls:
                return {"response": message.content}

            messages.append(message)

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                if "customer_id" not in args and CUSTOMER_ID:
                    args["customer_id"] = CUSTOMER_ID

                # Use live session
                result = await mcp_session.call_tool(tool_name, arguments=args)

                tool_result_text = "\n".join(
                    [getattr(item, "text", str(item)) for item in result.content]
                )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result_text
                })

        # Fallback if max iterations exceeded
        final_fallback = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        return {"response": final_fallback.choices[0].message.content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools")
async def list_available_tools():
    """Lists all tools and parameter schemas exposed by the Google Ads MCP server."""
    try:
        mcp_tools = await mcp_session.list_tools()
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
        raise HTTPException(status_code=500, detail=str(e))