<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('ads_analysis_logs', function (Blueprint $table) {
            $table->id();
            $table->string('type');
            $table->text('prompt')->nullable();
            $table->string('tool_name')->nullable();
            $table->json('arguments')->nullable();
            $table->longText('response')->nullable();
            $table->boolean('is_error')->default(false);
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('ads_analysis_logs');
    }
};