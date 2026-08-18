<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class AdsAnalysisLog extends Model
{
    protected $fillable = [
        'type',
        'prompt',
        'tool_name',
        'arguments',
        'response',
        'is_error',
    ];

    protected $casts = [
        'arguments' => 'array',
        'is_error' => 'boolean',
    ];
}