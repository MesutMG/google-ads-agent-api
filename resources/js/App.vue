<template>
  <div class="ads-container">
    <div class="main-card">
      <h1 class="page-title">Ads analyzer</h1>
      <hr class="divider" />

      <div class="input-group">
        <label for="prompt-input" class="input-label">Enter Prompt: </label>
        <div class="input-wrapper">
          <input 
            id="prompt-input"
            v-model="prompt"
            @keyup.enter="sendPrompt()"
            :disabled="isLoading"
            placeholder="e.g., How were the advertisements in May 2026?"
            class="prompt-input"
          />
          <button 
            @click="sendPrompt()" 
            :disabled="isLoading || !prompt"
            class="send-btn"
          >
            <span v-if="!isLoading">Send</span>
            <span v-else class="spinner"></span>
          </button>

          <button 
            @click="testPrompt()" 
            :disabled="isLoading || !prompt"
            class="send-btn"
          >
            <span v-if="!isLoading">Send Test</span>
            <span v-else class="spinner"></span>
          </button>
        </div>
      </div>

      <div class="response-section">
        <h3 class="response-title">Analysis Output:</h3>
        <div class="response-box" :class="{ 'loading-text': isLoading }">
          {{ data }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: "ads",
  data() {
    return {
      prompt: "",
      data: "Waiting for your question...",
      isLoading: false,
    };
  },

  methods: {
    async sendPrompt() {
      if (!this.prompt.trim() || this.isLoading) return;

      this.isLoading = true;
      this.data = "Analyzing your campaign data with OpenAI...";

      try {
        const response = await axios.post('/api/app/analyze', {
          prompt: this.prompt
        });

        this.data = response.data.answer || "No response content received.";
      } catch (error) {
        console.error("Error analyzing ads:", error);
        this.data = error.response?.data?.error 
          ? `Error: ${error.response.data.error}` 
          : "An error occurred while fetching the analysis. Please try again.";
      } finally {
        this.isLoading = false;
      }
    },

    async testPrompt() {
      if (!this.prompt.trim() || this.isLoading) return;

      this.isLoading = true;
      this.data = "Analyzing your campaign data with OpenAI...";

      try {
        const response = await axios.post('/api/app/test', {
          prompt: this.prompt
        });

        this.data = response.data.answer || "No response content received.";
      } catch (error) {
        console.error("Error analyzing ads:", error);
        this.data = error.response?.data?.error 
          ? `Error: ${error.response.data.error}` 
          : "An error occurred while fetching the analysis. Please try again.";
      } finally {
        this.isLoading = false;
      }
    },
  },
};
</script>

<style scoped>
.ads-container {
  display: flex;
  justify-content: center;
  padding: 2rem;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background-color: #f8fafc;
  min-height: 100vh;
}

.main-card {
  width: 100%;
  max-width: 700px;
  background: #ffffff;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  height: fit-content;
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

.input-group {
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
  gap: 0.5rem;
}

.prompt-input {
  flex: 1;
  padding: 0.75rem 1rem;
  font-size: 0.95rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  outline: none;
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
  white-space: pre-wrap;
  min-height: 100px;
}

.loading-text {
  color: #64748b;
  font-style: italic;
}

/* Loading Spinner */
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
</style>