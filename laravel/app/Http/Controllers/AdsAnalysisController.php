<?php

namespace App\Http\Controllers;

use App\Models\AdsAnalysisLog;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;

class AdsAnalysisController extends Controller
{
    public function analyze(Request $request) {
        $request->validate([
            'prompt' => 'required|string|max:2000',
        ]);

        $prompt = $request->input('prompt');
        $serviceUrl = config('services.python_ads.url') . '/chat';

        $response = Http::timeout(120)->post($serviceUrl, [
            'prompt' => $prompt,
        ]);

        if ($response->failed()) {
            AdsAnalysisLog::create([
                'type'     => 'ai_chat',
                'prompt'   => $prompt,
                'response' => json_encode($response->json() ?? $response->body()),
                'is_error' => true,
            ]);

            return response()->json([
                'error'   => 'Failed to process ad analysis with AI.',
                'details' => $response->json() ?? $response->body()
            ], $response->status() === 0 ? 500 : $response->status());
        }

        $answer = $response->json('response');

        // Store successful AI interaction
        AdsAnalysisLog::create([
            'type'     => 'ai_chat',
            'prompt'   => $prompt,
            'response' => $answer,
            'is_error' => false,
        ]);

        return response()->json([
            'answer' => $answer
        ]);
    }

    public function test_noAI(Request $request)
    {
        $request->validate([
            'tool_name' => 'required|string',
            'arguments' => 'nullable|array',
        ]);

        $toolName = $request->input('tool_name');
        $arguments = $request->input('arguments', []);
        $serviceUrl = config('services.python_ads.url') . '/execute-tool';

        $response = Http::timeout(60)->post($serviceUrl, [
            'tool_name' => $toolName,
            'arguments' => $arguments,
        ]);

        if ($response->failed()) {
            AdsAnalysisLog::create([
                'type'      => 'tool_direct',
                'tool_name' => $toolName,
                'arguments' => $arguments,
                'response'  => json_encode($response->json() ?? $response->body()),
                'is_error'  => true,
            ]);

            return response()->json([
                'error'   => 'Failed to execute MCP test tool.',
                'details' => $response->json() ?? $response->body(),
            ], $response->status() === 0 ? 500 : $response->status());
        }

        $resultData = $response->json();
        $formattedData = json_encode($resultData['data'] ?? [], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
        $answer = "```json\n" . $formattedData . "\n```";

        // Store direct tool execution
        AdsAnalysisLog::create([
            'type'      => 'tool_direct',
            'tool_name' => $toolName,
            'arguments' => $arguments,
            'response'  => $answer,
            'is_error'  => $resultData['is_error'] ?? false,
        ]);

        return response()->json([
            'tool'     => $resultData['tool'] ?? $toolName,
            'is_error' => $resultData['is_error'] ?? false,
            'answer'   => $answer,
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

    public function history()
    {
        $logs = AdsAnalysisLog::latest()->take(50)->get();

        return response()->json([
            'history' => $logs
        ]);
    }
}