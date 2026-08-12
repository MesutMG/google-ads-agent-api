<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;

class AdsAnalysisController extends Controller
{
    public function analyze(Request $request) {
        $request->validate([
            'prompt' => 'required|string|max:1000',
        ]);

        $serviceUrl = config('services.python_ads.url') . '/analyze-ads';

        //high timeout, might take long
        $response = Http::timeout(60)->post($serviceUrl, [
            'user_prompt' => $request->input('prompt'),
        ]);

        if ($response->failed()) {
            return response()->json([
                'error' => 'Failed to process ad analysis.',
                'details' => $response->json()
            ], 500);
        }

        return response()->json([
            'answer' => $response->json('response')
        ]);
    }

        public function test(Request $request) {
        $request->validate([
            'prompt' => 'required|string|max:1000',
        ]);

        $serviceUrl = config('services.python_ads.url') . '/test-pull';

        //high timeout, might take long
        $response = Http::timeout(60)->post($serviceUrl, [
            'user_prompt' => $request->input('prompt'),
        ]);

        if ($response->failed()) {
            return response()->json([
                'error' => 'Failed to process ad analysis.',
                'details' => $response->json()
            ], 500);
        }

        return response()->json([
            'answer' => $response->json('response')
        ]);
    }
}
