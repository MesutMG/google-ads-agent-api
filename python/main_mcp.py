import os
import json
import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

app = FastAPI()

with open("config.json", "r") as f:
    config = json.load(f)
with open("client_secret.json", "r") as f:
    client_secret = json.load(f)

openai_client = OpenAI(api_key=config["openai_api_key"])
CUSTOMER_ID = config.get("google_ads_customer_id", "")
PROJECT_ID = client_secret.get("project_id", "")
DEVELOPER_TOKEN = config.get("developer_token", "")

class ChatRequest(BaseModel):
    user_prompt: str

@app.post("/analyze-ads")
async def analyze_ads(request: ChatRequest):
    print(f"\n========== NEW REQUEST ==========")
    print(f"User Prompt: {request.user_prompt}")
    
    yaml_path = os.path.abspath("google-ads.yaml")
    server_env = dict(os.environ)
    server_env["GOOGLE_ADS_CONFIGURATION_FILE_PATH"] = yaml_path
    server_env["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID
    server_env["GOOGLE_ADS_DEVELOPER_TOKEN"] = DEVELOPER_TOKEN

    server_params = StdioServerParameters(
        command="python",
        args=["-m", "ads_mcp.server"], 
        env=server_env
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                mcp_tools = await session.list_tools()
                print("Available Tools: ", [tool.name for tool in mcp_tools.tools])
                openai_tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema
                        }
                    }
                    for tool in mcp_tools.tools
                ]
                
                print(f"[MCP] Successfully loaded {len(openai_tools)} tools.")

                system_prompt = (
                    f"Sen uzman bir Google Ads analistisin. Bugünün tarihi {datetime.date.today().isoformat()}. "
                    f"Analiz etmen gereken Google Ads Müşteri Kimliği: '{CUSTOMER_ID}'. "
                    "ZORUNLU KURALLAR: "
                    "1. Kullanıcı bir kampanya veya reklam grubu İSMİ verdiğinde (örn: 'Elmalı Reklam Grubu'), doğrudan bu metni ID bekleyen araçlara (tools) GİRME. "
                    "2. Her zaman iki adımlı işlem yap: ÖNCE arama/sorgu aracını kullanarak bu ismin sayısal ID'sini (Resource Name veya ID) veritabanından bul. SONRA bulduğun bu sayısal ID'yi veya kaynak adını kullanarak anahtar kelimeleri/metrikleri sorgula. "
                    "3. Canlı verileri sorgulamak için HER ZAMAN sana sunulan araçları kullan. "
                    "4. Hata alırsan mazeret uydurma (özel karakterler vb. halüsinasyonlar yapma), farklı bir sorgu veya araç ile tekrar dene. "
                    "5. Kullanıcıya asla 'bekle' veya 'zaman alacak' deme. "
                    "6. Nihai veri özetini her zaman Türkçe olarak sun. Cevabının sonuna KESİNLİKLE 'Başka bir konuda yardımcı olabilir miyim?' gibi kapanış veya takip soruları ekleme."
                )

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.user_prompt}
                ]

                # --- AGENT LOOP ---
                # Allow the LLM up to 5 iterations to call tools and get data
                MAX_ITERATIONS = 10
                
                for iteration in range(MAX_ITERATIONS):
                    print(f"\n--- [LLM] Iteration {iteration + 1} ---")
                    
                    response = openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=messages,
                        tools=openai_tools if openai_tools else None,
                        tool_choice="auto"
                    )
                    
                    response_message = response.choices[0].message
                    messages.append(response_message)

                    # If no tools were called, the LLM has generated its final answer
                    if not response_message.tool_calls:
                        print(f"[LLM] Final Answer Generated:")
                        print(f"{response_message.content}")
                        return {"response": response_message.content}

                    # Otherwise, execute the requested tools and loop again
                    for tool_call in response_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = tool_call.function.arguments
                        
                        print(f"\n[MCP] ---> Executing Tool: {tool_name}")
                        print(f"[MCP] ---> Arguments: {tool_args}")
                        
                        try:
                            mcp_result = await session.call_tool(
                                tool_name,
                                arguments=json.loads(tool_args)
                            )
                            result_text = str(mcp_result.content)
                            
                            # Print a snippet of the result to the terminal so it doesn't flood your screen
                            snippet = result_text[:300] + ("..." if len(result_text) > 300 else "")
                            print(f"[MCP] <--- Result: {snippet}")
                            
                        except Exception as tool_error:
                            result_text = f"Error executing tool: {tool_error}"
                            print(f"[MCP] <--- ERROR: {result_text}")

                        # Append the tool's result to the message history so the LLM can read it
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": tool_name,
                            "content": result_text,
                        })
                
                # If it exceeds MAX_ITERATIONS
                print("[Error] LLM exceeded maximum tool iterations.")
                return {"response": "I encountered an error trying to fetch the data. Please try a more specific query."}

    except Exception as e:
        import traceback
        print("\n--- CRITICAL ERROR ---")
        traceback.print_exc()
        print("----------------------\n")
        raise HTTPException(status_code=500, detail=str(e))