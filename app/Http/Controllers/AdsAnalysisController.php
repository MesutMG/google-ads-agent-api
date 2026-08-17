<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;

class AdsAnalysisController extends Controller
{
    /**
     * Connects to main_mcp.py (FastAPI with the OpenAI Agent)
     */
    public function analyze(Request $request) {
        $request->validate([
            'prompt' => 'required|string|max:2000', // Increased slightly for detailed user prompts
        ]);

        // Point to the new /chat endpoint defined in FastAPI
        $serviceUrl = config('services.python_ads.url') . '/chat';

        // High timeout is essential because the AI might execute multiple tools before answering
        $response = Http::timeout(120)->post($serviceUrl, [
            'prompt' => $request->input('prompt'),
        ]);

        if ($response->failed()) {
            return response()->json([
                'error' => 'Failed to process ad analysis with AI. Error fetch in AdsAnalysisController.php',
                'details' => $response->json() ?? $response->body()
            ], $response->status() === 0 ? 500 : $response->status());
        }

        return response()->json([
            'answer' => $response->json('response')
        ]);
    }

    /**
     * Connects to main_mcp_noAI.py (Direct Tool Execution without AI)
     * Useful if you want to bypass the AI and just pull raw JSON data using a tool name.
     */
    public function test_noAI(Request $request) {
        $request->validate([
            'tool_name' => 'required|string',
            'arguments' => 'nullable|array',
        ]);

        // Points to the /execute-tool endpoint defined in your original script
        $serviceUrl = config('services.python_ads.url') . '/execute-tool';

        $response = Http::timeout(60)->post($serviceUrl, [
            'tool_name' => $request->input('tool_name'),
            'arguments' => $request->input('arguments', []),
        ]);

        if ($response->failed()) {
            return response()->json([
                'error'   => 'Failed to execute MCP test tool. Error fetch in AdsAnalysisController.php',
                'details' => $response->json() ?? $response->body(),
            ], $response->status() === 0 ? 500 : $response->status());
        }

        $resultData = $response->json();

        // Convert the returned data structure into a formatted JSON string or markdown block for display
        $formattedData = json_encode($resultData['data'] ?? [], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);

        return response()->json([
            'tool'     => $resultData['tool'] ?? $request->input('tool_name'),
            'is_error' => $resultData['is_error'] ?? false,
            'answer'   => "```json\n" . $formattedData . "\n```",
            'raw_data' => $resultData['data'] ?? [],
        ]);
    }

    public function tools(Request $request) {
        $serviceUrl = config('services.python_ads.url') . '/tools';
        $response = Http::timeout(30)->get($serviceUrl);

        if ($response->failed()) {
            return response()->json([
                'error'   => 'Failed to get tools from Python MCP server.',
                'details' => $response->json() ?? $response->body()
            ], $response->status() === 0 ? 500 : $response->status());
        }

        return response()->json([
            'count' => $response->json('count'),
            'tools' => $response->json('tools')
        ]);
    }
}