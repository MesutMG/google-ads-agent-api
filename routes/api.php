<?php

use App\Http\Controllers\AdsAnalysisController;
use Illuminate\Support\Facades\Route;

Route::post('/app/analyze', [AdsAnalysisController::class, 'analyze']);
Route::post('/app/test', [AdsAnalysisController::class, 'test']);