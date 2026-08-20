<template>
  <div class="ads-container">
    <!-- Main Card -->
    <div class="main-card">
      <h1 class="page-title">Google Ads Analizi</h1>
      <hr class="divider" />

      <label for="prompt-input" class="input-label">Sorunuzu veya İsteminizi Girin: </label>
      <div class="input-wrapper">
        <textarea 
          id="prompt-input"
          v-model="prompt"
          @keydown.enter.exact.prevent="sendPrompt()"
          :disabled="isLoading"
          placeholder="örn. Ağustos 2026'daki kampanya performanslarım ve anahtar kelimelerim nasıldı?"
          class="prompt-input"
          rows="1"
        ></textarea>
      </div>

      <div class="buttons">
        <button 
          @click="sendPrompt()" 
          :disabled="isLoading || !prompt"
          class="send-btn"
        >
          <span v-if="!isLoading">Gönder</span>
          <span v-else class="spinner"></span>
        </button>

        <button
          @click="sendNoAIToolRequest()" 
          :disabled="isLoading"
          class="send-btn"
        >
          <span v-if="!isLoading">Tüm Verileri Çek</span>
          <span v-else class="spinner"></span>
        </button>

        <button
          @click="getTools()" 
          :disabled="isLoading"
          class="send-btn"
        >
          <span v-if="!isLoading">Araçları Getir</span>
          <span v-else class="spinner"></span>
        </button>
      </div>

      <div class="response-section">
        <h3 class="response-title">Analiz Çıktısı:</h3>
        <div 
          class="response-box" 
          :class="{ 'loading-text': isLoading }"
          v-html="parsedData"
        >
        </div>
      </div>
    </div>

    <!-- History Panel -->
    <div class="history-card">
      <div class="history-header">
        <h2 class="history-title">Geçmiş Analizler</h2>
        <button @click="fetchHistory()" :disabled="isLoadingHistory" class="refresh-btn">
          Yenile
        </button>
      </div>
      <hr class="divider" />

      <div v-if="isLoadingHistory" class="history-loading">
        Geçmiş yükleniyor...
      </div>

      <div v-else-if="history.length === 0" class="history-empty">
        Henüz kaydedilmiş bir geçmiş yok.
      </div>

      <div v-else class="history-list">
        <div 
          v-for="item in history" 
          :key="item.id" 
          class="history-item"
          @click="selectHistoryItem(item)"
        >
          <div class="history-item-top">
            <span class="badge" :class="item.type">
              {{ item.type === 'ai_chat' ? 'Yapay Zeka' : 'MCP Aracı' }}
            </span>
            <span class="history-date">{{ formatDate(item.created_at) }}</span>
          </div>
          <div class="history-prompt">
            {{ item.type === 'ai_chat' ? item.prompt : (item.tool_name || 'Doğrudan Araç Çağrısı') }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { marked } from 'marked';

export default {
  name: "ads",
  data() {
    return {
      prompt: "",
      data: "Sorunuz bekleniyor...",
      isLoading: false,
      history: [],
      isLoadingHistory: false,
    };
  },
  computed: {
    parsedData() {
      if (!this.data) return "";
      return marked(this.data);
    }
  },
  mounted() {
    this.fetchHistory();
  },
  methods: {
    async fetchHistory() {
      this.isLoadingHistory = true;
      try {
        const response = await axios.get('/api/app/history');
        this.history = response.data.history || [];
      } catch (error) {
        console.error("Geçmiş getirilemedi:", error);
      } finally {
        this.isLoadingHistory = false;
      }
    },

    selectHistoryItem(item) {
      this.prompt = item.prompt || "";
      this.data = item.response || "Bu kayıt için çıktı bulunmuyor.";
    },

    formatDate(dateString) {
      if (!dateString) return "";
      const d = new Date(dateString);
      return d.toLocaleDateString('tr-TR', { 
        day: '2-digit', 
        month: 'short', 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    },

    async sendPrompt() {
      if (!this.prompt.trim() || this.isLoading) return;

      this.isLoading = true;
      this.data = "Kampanya verileriniz OpenAI ve MCP araçları ile analiz ediliyor...";

      try {
        const response = await axios.post('/api/app/analyze', 
          JSON.stringify({ prompt: this.prompt }), 
          {
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json'
            }
          }
        );

        this.data = response.data.answer || "Herhangi bir yanıt içeriği alınamadı.";
        this.fetchHistory();
      } catch (error) {
        console.error("Reklam analiz hatası:", error);
        this.data = error.response?.data?.message 
          ? `Hata: ${error.response.data.message}` 
          : "Analiz getirilirken bir hata oluştu. Lütfen tekrar deneyin.";
      } finally {
        this.isLoading = false;
      }
    },

    async testPrompt() {
      if (!this.prompt.trim() || this.isLoading) return;

      this.isLoading = true;
      this.data = "Kampanya verileriniz analiz ediliyor...";

      try {
        const response = await axios.post('/api/app/test', 
          JSON.stringify({ prompt: this.prompt }), 
          {
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json'
            }
          }
        );

        this.data = response.data.answer || "Herhangi bir yanıt içeriği alınamadı.";
        this.fetchHistory();
      } catch (error) {
        console.error("Test analiz hatası:", error);
        this.data = error.response?.data?.message 
          ? `Hata: ${error.response.data.message}` 
          : "Analiz getirilirken bir hata oluştu. Lütfen tekrar deneyin.";
      } finally {
        this.isLoading = false;
      }
    },

    async sendNoAIToolRequest() {
      if (this.isLoading) return;

      this.isLoading = true;
      this.data = "Ham veriler doğrudan Google Ads MCP üzerinden çekiliyor...";

      try {
        const response = await axios.post('/api/app/test-no-ai', {
          tool_name: "get_account_performance_summary",
          arguments: {
            date_range: "LAST_30_DAYS"
          }
        }, {
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          }
        });

        this.data = response.data.answer || "Herhangi bir yanıt içeriği alınamadı.";
        this.fetchHistory();
      } catch (error) {
        console.error("MCP araç çalıştırma hatası:", error);
        this.data = error.response?.data?.error 
          ? `Hata: ${error.response.data.error}` 
          : "Veriler çekilirken bir hata oluştu.";
      } finally {
        this.isLoading = false;
      }
    },

    async getTools() {
      if (this.isLoading) return;

      this.isLoading = true;
      this.data = "Google Ads MCP araçları listeleniyor...";

      try {
        const response = await axios.post('/api/app/tools', {}, {
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          }
        });

        const count = response.data.count ?? 0;
        const tools = response.data.tools ?? [];

        const formattedList = tools
          .map((t, idx) => `${idx + 1}. **${t.name}**\n   ${t.description || 'Açıklama bulunmuyor.'}`)
          .join('\n\n');

        this.data = `Toplam araç sayısı: ${count}\n\n${formattedList}`;
      } catch (error) {
        console.error("MCP araç listesi hatası:", error);
        this.data = error.response?.data?.error 
          ? `Hata: ${error.response.data.error}` 
          : "Araç verileri çekilirken bir hata oluştu.";
      } finally {
        this.isLoading = false;
      }
    }
  },
};
</script>

<style scoped>
.ads-container {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  gap: 1.5rem;
  padding: 2rem;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background-color: #f8fafc;
  min-height: 100vh;
  box-sizing: border-box;
}

.main-card {
  flex: 1;
  max-width: 700px;
  background: #ffffff;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.history-card {
  width: 320px;
  background: #ffffff;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.history-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}

.refresh-btn {
  background: none;
  border: 1px solid #cbd5e1;
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  font-size: 0.8rem;
  color: #475569;
  cursor: pointer;
}

.refresh-btn:hover {
  background-color: #f1f5f9;
}

.history-list {
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding-right: 0.25rem;
}

.history-item {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.75rem;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
}

.history-item:hover {
  border-color: #2563eb;
  background-color: #f8fafc;
}

.history-item-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.4rem;
}

.badge {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
}

.badge.ai_chat {
  background-color: #dbeafe;
  color: #1d4ed8;
}

.badge.tool_direct {
  background-color: #fef3c7;
  color: #b45309;
}

.history-date {
  font-size: 0.75rem;
  color: #94a3b8;
}

.history-prompt {
  font-size: 0.85rem;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-loading, .history-empty {
  font-size: 0.85rem;
  color: #94a3b8;
  font-style: italic;
  text-align: center;
  padding: 1rem 0;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.5rem 0;
}

.divider {
  border: 0;
  height: 1px;
  background: #e2e8f0;
  margin-bottom: 1.5rem;
}

.input-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: #475569;
  margin-bottom: 0.5rem;
}

.input-wrapper {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.prompt-input {
  width: 100%;
  flex: 1 1 100%;
  min-height: 44px;
  max-height: 200px;
  field-sizing: content;
  padding: 0.75rem 1rem;
  font-size: 0.95rem;
  font-family: inherit;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  outline: none;
  resize: none;
  overflow-y: auto;
  line-height: 1.5;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.prompt-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

.prompt-input:disabled {
  background-color: #f1f5f9;
  cursor: not-allowed;
}

.buttons {
  padding: 10px 0;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.send-btn {
  padding: 0.75rem 1.5rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: #ffffff;
  background-color: #2563eb;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 80px;
}

.send-btn:hover:not(:disabled) {
  background-color: #1d4ed8;
}

.send-btn:disabled {
  background-color: #94a3b8;
  cursor: not-allowed;
}

.response-section {
  margin-top: 1.5rem;
}

.response-title {
  font-size: 1rem;
  font-weight: 600;
  color: #334155;
  margin-bottom: 0.5rem;
}

.response-box {
  background-color: #f1f5f9;
  border-left: 4px solid #2563eb;
  padding: 1rem 1.25rem;
  border-radius: 0 8px 8px 0;
  color: #1e293b;
  font-size: 0.95rem;
  line-height: 1.6;
  min-height: 100px;
}

.response-box :deep(p) {
  margin-top: 0;
  margin-bottom: 1rem;
}

.response-box :deep(p:last-child) {
  margin-bottom: 0;
}

.response-box :deep(ul) {
  margin-top: 0;
  margin-bottom: 1rem;
  padding-left: 1.5rem;
}

.response-box :deep(li) {
  margin-bottom: 0.25rem;
}

.response-box :deep(strong) {
  font-weight: 600;
  color: #0f172a;
}

.loading-text {
  color: #64748b;
  font-style: italic;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #ffffff;
  border-bottom-color: transparent;
  border-radius: 50%;
  display: inline-block;
  animation: rotation 1s linear infinite;
}

@keyframes rotation {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@media (max-width: 900px) {
  .ads-container {
    flex-direction: column;
    align-items: stretch;
  }
  .history-card {
    width: 100%;
    max-height: 400px;
  }
}
</style>