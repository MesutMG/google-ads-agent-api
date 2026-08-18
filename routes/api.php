<?php

use App\Http\Controllers\AdsAnalysisController;
use Illuminate\Support\Facades\Route;

Route::post('/app/analyze', [AdsAnalysisController::class, 'analyze']);
Route::post('/app/tools', [AdsAnalysisController::class, 'tools']);
Route::post('/app/test-no-ai', [AdsAnalysisController::class, 'test_noAI']);
Route::get('/app/history', [AdsAnalysisController::class, 'history']);