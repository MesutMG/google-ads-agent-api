import os
import json
import shutil
from datetime import datetime, date
from typing import Any, Dict, Optional, Union, List
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
LOG_FILE_PATH = os.path.join(BASE_DIR, "mcp_debug.log")
UV_BIN = shutil.which("uv") or "uv"

config: Dict[str, Any] = {}
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

def get_env_or_config(key: str, default: str = "") -> str:
    return os.getenv(key.upper(), config.get(key, default))


def write_debug_log(content: str):
    with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
        f.write(content + "\n")


def get_mcp_server_params() -> StdioServerParameters:
    server_env = os.environ.copy()
    server_env["GOOGLE_ADS_DEVELOPER_TOKEN"] = get_env_or_config("developer_token")
    server_env["GOOGLE_ADS_CLIENT_ID"] = get_env_or_config("client_id")
    server_env["GOOGLE_ADS_CLIENT_SECRET"] = get_env_or_config("client_secret")
    server_env["GOOGLE_ADS_REFRESH_TOKEN"] = get_env_or_config("refresh_token")
    server_env["GOOGLE_ADS_LOGIN_CUSTOMER_ID"] = get_env_or_config("login_customer_id")

    return StdioServerParameters(
        command=UV_BIN,
        args=["run", "--directory", MCP_DIR, "google-ads-mcp"],
        cwd=MCP_DIR,
        env=server_env
    )

# --- GLOBAL MCP SESSION & OPENAI CLIENT ---
mcp_stack = AsyncExitStack()
mcp_session: Optional[ClientSession] = None
cached_openai_tools: List[Dict[str, Any]] = []
openai_client: Optional[AsyncOpenAI] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mcp_session, cached_openai_tools, openai_client

    openai_api_key = get_env_or_config("openai_api_key")
    if not openai_api_key:
        raise RuntimeError("OpenAI API Key is missing.")
    openai_client = AsyncOpenAI(api_key=openai_api_key)

    try:
        read, write = await mcp_stack.enter_async_context(stdio_client(get_mcp_server_params()))
        mcp_session = await mcp_stack.enter_async_context(ClientSession(read, write))
        await mcp_session.initialize()

        tools_response = await mcp_session.list_tools()
        cached_openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.inputSchema
                }
            }
            for t in tools_response.tools
        ]
        yield
    finally:
        await mcp_stack.aclose()
        if openai_client:
            await openai_client.close()

app = FastAPI(lifespan=lifespan)

# --- Pydantic Models ---
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    account_no: Union[str, int]
    messages: List[Message]

@app.post("/chat")
async def chat_with_agent(request: ChatRequest):
    if not mcp_session or not openai_client:
        raise HTTPException(
            status_code=503, 
            detail="MCP Server session is not initialized."
        )

    log_header = (
        f"\n{'#' * 80}\n"
        f" - [NEW REQUEST - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n"
        f" - [ACCOUNT NO]: {request.account_no}\n"
        f" - [LAST USER MESSAGE]: {request.messages[-1].content if request.messages else 'Empty'}\n"
        f"{'#' * 80}\n"
    )
    write_debug_log(log_header)

    SYSTEM_PROMPT = (
        f"Sen uzman bir Google Ads analistisin. Bugünün tarihi {date.today().isoformat()}. "
        f"Analiz etmen gereken Google Ads Müşteri Kimliği (Customer ID): '{request.account_no}'. "
        "Kurallar: "
        "1. Yetki sınırı ve Read-Only kuralı: Sen yalnızca salt okunur (read-only) bir analiz asistanısın. Kampanya, reklam grubu, anahtar kelime veya bütçe oluşturma, düzenleme, silme veya güncelleme yetkin yoktur. Kullanıcı böyle bir talepte bulunursa hiçbir araç çağırma ve doğrudan '<p>Kampanya oluşturmak veya düzenlemek gibi bir yetkim yok, yalnızca analiz ve okuma (read-only) yapabilirim.</p>' şeklinde net bir yanıt ver. "
        "2. Kullanıcı bir kampanya veya reklam grubu ismi verdiğinde, doğrudan bu metni ID bekleyen araçlara girme. "
        "3. Her zaman iki adımlı işlem yap: önce arama aracıyla sayısal ID'yi bul, sonra bu ID ile metrikleri sorgula. "
        "4. Canlı verileri sorgulamak için her zaman sana sunulan araçları kullan. "
        "5. Hata alırsan mazeret uydurma, farklı bir sorgu veya araç ile tekrar dene. "
        "6. Kullanıcıya asla 'bekle' veya 'kontrol ediyorum' diyerek aracı çağırmadan yanıt verme. Gerekli tüm araçları sırayla çağırıp analizi tamamla. "
        "7. Genel bilgi vermek yasaktır: yalnızca hesaptaki spesifik verilere dayanarak matematiksel tahmin yap. Jenerik sektör trendleri uydurma. "
        "8. Para birimi kuralı: API'den gelen 'cost_micros' ve 'average_cpc' değerleri micros formatındadır. Bu değerleri tam olarak 1.000.000'a (bir milyona) bölerek TL cinsine çevir. Örnek: 848454780 micros = 848.45 TL (0.85 TL değil), 719984780 micros = 719.98 TL (0.72 TL değil). Asla 1 milyara veya 100 milyona bölme. Ayrıca bu formatı kullan: 1.234.567,89 virgülden sonra her zaman 2 rakam kullan."
        "9. Nihai veri özetini her zaman Türkçe olarak sun. Cevabının sonuna kapanış veya takip soruları ekleme. "
        "10. HTML Format Kuralı: Yanıtında markdown sözdizimi (#, ##, **, *, _, -) veya html kod bloğu kullanma. Yanıtını doğrudan HTML etiketleri (<h3>, <h4>, <p>, <strong>, <ul>, <li>, <table class='table table-bordered'> vb.) ile formatlayarak saf HTML döndür."
    )

    messages_context: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in request.messages:
        messages_context.append({"role": msg.role, "content": msg.content})

    max_iterations = 8

    for iteration in range(max_iterations):
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages_context,
                tools=cached_openai_tools or None
            )
        except Exception as e:
            error_log = f" - [OPENAI API ERROR]: {str(e)}"
            write_debug_log(error_log)
            raise HTTPException(
                status_code=502, detail=f"OpenAI completion error: {str(e)}"
            )

        choice = response.choices[0]
        message = choice.message

        if not message.tool_calls:
            write_debug_log(
                f" - [FINAL ASSISTANT RESPONSE]:\n{message.content}\n{'#' * 80}\n"
            )
            return {"response": message.content}

        messages_context.append(message.model_dump(exclude_none=True))

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            raw_args = tool_call.function.arguments

            log_entry = [
                "=" * 80,
                f" - [TOOL INVOKED | ITERATION {iteration + 1}]: {tool_name}",
                f" - [CALL ID]: {tool_call.id}",
            ]

            try:
                args = json.loads(raw_args)
                args.setdefault("customer_id", str(request.account_no))
                log_entry.append(
                    f" - [ARGUMENTS]:\n{json.dumps(args, indent=2, ensure_ascii=False)}"
                )
            except Exception as parse_err:
                args = {"customer_id": str(request.account_no)}
                log_entry.append(
                    f" --- [ARGUMENT PARSE WARNING]: {parse_err}\nRaw arguments: {raw_args}"
                )

            log_entry.append("-" * 80)

            try:
                result = await mcp_session.call_tool(tool_name, arguments=args)

                raw_chunks = [
                    getattr(item, "text", str(item))
                    for item in getattr(result, "content", [])
                ]
                tool_result_text = "\n".join(raw_chunks)

                log_entry.append(" - [MCP RESPONSE / COLUMNS / ROWS]:")
                try:
                    parsed_result = json.loads(tool_result_text)
                    log_entry.append(
                        json.dumps(parsed_result, indent=2, ensure_ascii=False)
                    )
                except Exception:
                    log_entry.append(tool_result_text)

            except Exception as err:
                tool_result_text = f"Tool Execution Error ({tool_name}): {str(err)}"
                log_entry.append(f" - [MCP EXECUTION ERROR]:\n{tool_result_text}")

            log_entry.append("=" * 80)
            write_debug_log("\n".join(log_entry))

            messages_context.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result_text
            })

    final_fallback = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages_context
    )
    final_content = final_fallback.choices[0].message.content
    write_debug_log(
        f" - [FALLBACK ASSISTANT RESPONSE]:\n{final_content}\n{'#' * 80}\n"
    )
    return {"response": final_content}
