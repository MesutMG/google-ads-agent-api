<?php

namespace App\Console\Commands;

use App\Models\AdsAnalysisLog;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class RunDailyAdsAnalysis extends Command
{
    protected $signature = 'ads:daily-analysis';
    protected $description = 'Runs the automated daily Google Ads analysis prompt via FastAPI MCP';

    public function handle()
    {
        $this->info('Starting automated daily ads analysis...');

        $dailyPrompt = "Dünkü ve son 7 günün Google Ads performansını incele. "
                     . "Toplam harcama (TL cinsinden), tıklama, gösterim, dönüşüm verilerini "
                     . "ve dikkat edilmesi gereken anomalileri maddeler halinde özetle.";

        $serviceUrl = config('services.python_ads.url') . '/chat';

        try {
            $response = Http::timeout(180)->post($serviceUrl, [
                'prompt' => $dailyPrompt,
            ]);

            if ($response->failed()) {
                AdsAnalysisLog::create([
                    'type'     => 'ai_chat',
                    'prompt'   => $dailyPrompt . ' (Otomatik Günlük Rapor)',
                    'response' => json_encode($response->json() ?? $response->body()),
                    'is_error' => true,
                ]);

                $this->error('Failed to receive response from AI.');
                return Command::FAILURE;
            }

            $answer = $response->json('response');

            // 1. Save to Database
            $log = AdsAnalysisLog::create([
                'type'     => 'ai_chat',
                'prompt'   => $dailyPrompt . ' (Otomatik Günlük Rapor)',
                'response' => $answer,
                'is_error' => false,
            ]);

            $this->info('Analysis saved to database successfully.');

            // 2. Send Notification
            $this->sendNotification($answer);

            return Command::SUCCESS;
        } catch (\Exception $e) {
            Log::error('Daily Ads Analysis Command Error: ' . $e->getMessage());
            $this->error('Exception: ' . $e->getMessage());
            return Command::FAILURE;
        }
    }

    /**
     * Send instant notification (e.g. Telegram, Discord Webhook, or Email)
     */
    protected function sendNotification(string $analysisText)
    {
        // Example: Sending to a Discord/Slack webhook or Telegram Bot
        $webhookUrl = env('DISCORD_OR_SLACK_WEBHOOK_URL');

        if ($webhookUrl) {
            Http::post($webhookUrl, [
                'content' => "📊 **Günlük Google Ads Raporu (08:00)**\n\n" . substr($analysisText, 0, 1900)
            ]);
        }
    }
}