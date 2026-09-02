import os
import json
import shutil
import asyncio
import traceback
from datetime import datetime, date
from typing import Any, Dict, Optional, Union, List
from contextlib import AsyncExitStack, asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import AsyncOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# -- SUBPROJECT IMPORTS --
from comment_analyzer.src.preprocess import Preprocessor
from comment_analyzer.src.filter import Filter
from comment_analyzer.src.analyze import Analyzer

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


# ==============================================================================
# 1. GOOGLE ADS CHAT ENDPOINT WITH DEBUG LOGGING
# ==============================================================================

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
        f" - [NEW ADS CHAT REQUEST - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n"
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

    messages_context: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    for msg in request.messages:
        messages_context.append({"role": msg.role, "content": msg.content})

    max_iterations = 8

    for iteration in range(max_iterations):
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages_context,
                tools=cached_openai_tools or None,
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


# ==============================================================================
# 2. COMMENT MODERATION & ANALYSIS WITH PIPELINE DEBUG LOGGING
# ==============================================================================

class CommentItem(BaseModel):
    id: Optional[Union[int, str]] = None
    comment: str
    star: Optional[float] = 5.0
    name: Optional[str] = None
    email: Optional[str] = None
    pnr: Optional[str] = None


class CommentAnalysisRequest(BaseModel):
    comments: List[CommentItem]
    max_llm_rows: Optional[int] = None


def correct_star_rating(row: pd.Series) -> float:
    try:
        star = float(row.get("star", 1.0))
    except (ValueError, TypeError):
        return 1.0

    sentiment = str(row.get("degerlendirme", "")).lower()

    if sentiment == "negatif" and star == 5.0:
        return 3.0
    if sentiment == "pozitif" and star in [1.0, 2.0]:
        return 4.0

    return star


def run_comment_pipeline_sync(
    comments_data: List[Dict[str, Any]], max_rows: Optional[int] = None
) -> Dict[str, Any]:
    if not comments_data:
        write_debug_log(" - [PIPELINE ABORTED]: Empty comment payload received.")
        return {"total_count": 0, "approved_count": 0, "records": []}

    initial_count = len(comments_data)
    df = pd.DataFrame(comments_data)

    # 1. Preprocess
    preprocessor = Preprocessor()
    df = preprocessor.process(df)
    preprocessed_count = len(df)
    dropped_preprocess = initial_count - preprocessed_count

    write_debug_log(
        f" - [STAGE 1 | PREPROCESS]: {initial_count} received -> {preprocessed_count} retained "
        f"({dropped_preprocess} dropped due to empty/PII)"
    )

    if df.empty:
        write_debug_log(" - [STAGE 1 | PREPROCESS]: All rows were dropped.")
        return {"total_count": 0, "approved_count": 0, "records": []}

    # 2. Static Filter
    comment_filter = Filter()
    df_clean, df_flagged = comment_filter.filter(df)
    clean_count = len(df_clean)
    flagged_static_count = len(df_flagged)

    write_debug_log(
        f" - [STAGE 2 | REGEX FILTER]: {clean_count} passed to LLM, {flagged_static_count} flagged statically."
    )
    if not df_flagged.empty and "flag_category" in df_flagged.columns:
        cat_summary = df_flagged["flag_category"].value_counts().to_dict()
        write_debug_log(f"   └── Static Categories: {json.dumps(cat_summary, ensure_ascii=False)}")

    # 3. LLM Analysis
    analyzer = Analyzer()
    df_analyzed = analyzer.run_pipeline(df_clean, max_rows=max_rows)
    llm_flagged_count = 0
    if "llm_uygunsuz" in df_analyzed.columns:
        llm_flagged_count = int(df_analyzed["llm_uygunsuz"].fillna(False).sum())

    write_debug_log(
        f" - [STAGE 3 | OLLAMA ANALYZER]: {len(df_analyzed)} evaluated, {llm_flagged_count} flagged by model."
    )

    # 4. Fill defaults for statically flagged rows
    if not df_flagged.empty:
        df_flagged["degerlendirme"] = "negatif"
        df_flagged["kategori"] = df_flagged["flag_category"].str.lower()
        df_flagged["llm_uygunsuz"] = True
        df_flagged["llm_sebep"] = "Statik kural motoru tarafından engellendi."

    # 5. Combine Datasets
    df_final = pd.concat([df_analyzed, df_flagged], ignore_index=True)

    # 6. Star Rating Correction
    if "star" in df_final.columns:
        df_final["star"] = df_final.apply(correct_star_rating, axis=1)
        write_debug_log(" - [STAGE 4 | STAR CORRECTION]: Heuristic adjustments applied.")

    # 7. Final Classification
    clean_mask = (~df_final["is_flagged"].fillna(False)) & (
        df_final["llm_uygunsuz"].fillna(False) == False
    )

    all_records = df_final.to_dict(orient="records")
    approved_records = df_final[clean_mask].to_dict(orient="records")

    summary_log = (
        f" - [STAGE 5 | FINAL VERDICT]: Total: {len(all_records)} | "
        f"Approved: {len(approved_records)} | Rejected: {len(all_records) - len(approved_records)}"
    )
    write_debug_log(summary_log)

    return {
        "success": True,
        "total_count": len(all_records),
        "approved_count": len(approved_records),
        "approved_comments": approved_records,
        "all_comments": all_records,
    }


@app.post("/comments/analyze")
async def analyze_comments(request: CommentAnalysisRequest):
    req_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_header = (
        f"\n{'#' * 80}\n"
        f" - [NEW BATCH COMMENT ANALYSIS - {req_time}]\n"
        f" - [BATCH SIZE]: {len(request.comments)} items\n"
        f" - [MAX LLM ROWS]: {request.max_llm_rows or 'No Limit'}\n"
        f"{'#' * 80}"
    )
    write_debug_log(log_header)

    try:
        data = [c.model_dump() for c in request.comments]
        result = await asyncio.to_thread(
            run_comment_pipeline_sync, data, request.max_llm_rows
        )
        write_debug_log(f"{'#' * 80}\n")
        return result
    except Exception as e:
        err_trace = traceback.format_exc()
        write_debug_log(f" - [BATCH ANALYSIS ERROR]: {str(e)}\n{err_trace}\n{'#' * 80}\n")
        raise HTTPException(
            status_code=500, detail=f"Batch comment analysis failed: {str(e)}"
        )


@app.post("/comment/analyze")
async def analyze_single_comment(comment: CommentItem):
    req_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    preview_text = (comment.comment[:75] + "...") if len(comment.comment) > 75 else comment.comment
    log_header = (
        f"\n{'#' * 80}\n"
        f" - [NEW SINGLE COMMENT ANALYSIS - {req_time}]\n"
        f" - [COMMENT ID]: {comment.id or 'N/A'}\n"
        f" - [CONTENT PREVIEW]: \"{preview_text}\"\n"
        f"{'#' * 80}"
    )
    write_debug_log(log_header)

    try:
        data = [comment.model_dump()]
        result = await asyncio.to_thread(run_comment_pipeline_sync, data)

        if not result["all_comments"]:
            write_debug_log(" - [SINGLE ANALYSIS]: Comment could not be processed (dropped).")
            write_debug_log(f"{'#' * 80}\n")
            raise HTTPException(
                status_code=400,
                detail="Comment was empty or could not be processed.",
            )

        processed_comment = result["all_comments"][0]
        is_approved = (
            not processed_comment.get("is_flagged", False)
            and not processed_comment.get("llm_uygunsuz", False)
        )

        single_result_log = (
            f" - [SINGLE RESULT]: Approved = {is_approved} | "
            f"Sentiment = {processed_comment.get('degerlendirme', 'N/A')} | "
            f"Category = {processed_comment.get('kategori', 'N/A')} | "
            f"Final Star = {processed_comment.get('star', 'N/A')}\n"
            f"{'#' * 80}\n"
        )
        write_debug_log(single_result_log)

        return {
            "success": True,
            "is_approved": is_approved,
            "comment": processed_comment,
        }
    except HTTPException:
        raise
    except Exception as e:
        err_trace = traceback.format_exc()
        write_debug_log(f" - [SINGLE ANALYSIS ERROR]: {str(e)}\n{err_trace}\n{'#' * 80}\n")
        raise HTTPException(
            status_code=500, detail=f"Single comment analysis failed: {str(e)}"
        )