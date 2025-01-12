<template>
  <div class="page-container">
    <button class="menu-toggle" @click="toggleMenu">
      {{ isMenuOpen ? '×' : '☰' }}
    </button>

    <button class="options-toggle" @click="toggleOptions">
      ⚙️
    </button>

    <SideMenu 
      :is-open="isMenuOpen"
      :chats="chats"
      :current-chat-id="currentChatId"
      @toggle="toggleMenu"
      @new-chat="createNewChat"
      @select-chat="loadChat"
    />

    <div class="content-container">
      <div class="chat-container">
        <div class="header">
          <h1>Simple Chat</h1>
        </div>
        
        <ChatMessages 
          :messages="messages" 
          :streaming-content="streamingContent"
          ref="chatMessages"
        />

        <ChatInput 
          ref="chatInput"
          @send="sendMessage"
          :disabled="isStreaming"
        />
      </div>
    </div>

    <OptionsDialog
      :is-open="isOptionsOpen"
      :api-key="apiKey"
      :selected-model="selectedModel"
      :dark-mode="darkMode"
      @close="closeOptions"
      @save="saveOptions"
    />
  </div>
</template>

<script>
import ChatInput from './components/ChatInput.vue'
import ChatMessages from './components/ChatMessages.vue'
import SideMenu from './components/SideMenu.vue'
import OptionsDialog from './components/OptionsDialog.vue'

export default {
  name: 'App',
  
  components: {
    ChatInput,
    ChatMessages,
    SideMenu,
    OptionsDialog
  },

  data() {
    return {
      messages: [],
      chats: [],
      currentChatId: null,
      isMenuOpen: false,
      isOptionsOpen: false,
      apiKey: '',
      selectedModel: 'claude-3-opus',
      darkMode: false,
      streamingContent: '',
      isStreaming: false
    }
  },

  async mounted() {
    window.addEventListener('resize', this.adjustMessageContainerHeight);
    this.adjustMessageContainerHeight();
    await this.loadChats();
    if (!this.currentChatId) {
      await this.createNewChat();
    }
    this.loadOptions();
    this.$refs.chatInput.focus();
  },

  beforeDestroy() {
    window.removeEventListener('resize', this.adjustMessageContainerHeight);
  },

  methods: {
    toggleMenu() {
      this.isMenuOpen = !this.isMenuOpen;
    },

    toggleOptions() {
      this.isOptionsOpen = !this.isOptionsOpen;
    },

    closeOptions() {
      this.isOptionsOpen = false;
    },

    saveOptions(options) {
      this.apiKey = options.apiKey;
      this.selectedModel = options.selectedModel;
      this.darkMode = options.darkMode;
      
      localStorage.setItem('apiKey', this.apiKey);
      localStorage.setItem('selectedModel', this.selectedModel);
      localStorage.setItem('darkMode', this.darkMode);
      
      this.closeOptions();
    },

    loadOptions() {
      this.apiKey = localStorage.getItem('apiKey') || '';
      this.selectedModel = localStorage.getItem('selectedModel') || 'claude-3-opus';
      this.darkMode = localStorage.getItem('darkMode') === 'true';
    },

    async loadChats() {
      try {
        const response = await fetch('/api/chats');
        this.chats = await response.json();
      } catch (error) {
        console.error('Error loading chats:', error);
      }
    },

    async createNewChat() {
      this.currentChatId = Date.now().toString();
      this.messages = [];
      await this.loadChats();
      this.isMenuOpen = false;
    },

    async loadChat(chatId) {
      try {
        const response = await fetch(`/api/chats/${chatId}`);
        const chatData = await response.json();
        this.messages = chatData.messages;
        this.currentChatId = chatId;
        this.isMenuOpen = false;
      } catch (error) {
        console.error('Error loading chat:', error);
      }
    },

    adjustMessageContainerHeight() {
      const header = document.querySelector('.header').offsetHeight;
      const input = document.querySelector('.input-container').offsetHeight;
      const windowHeight = window.innerHeight;
      const messageContainer = this.$refs.chatMessages.$el;
      messageContainer.style.height = `${windowHeight - header - input - 40}px`;
    },

    async sendMessage(message) {
      // ストリーミング開始前の準備
      this.isStreaming = true;
      this.streamingContent = '';

      // 即座にユーザーメッセージを表示
      this.messages.push({
        role: 'user',
        content: message,
        timestamp: new Date().toISOString()
      });

      try {
        const response = await fetch(`/api/chats/${this.currentChatId}/messages`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            message: message,
            stream: true
          })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.chunk) {
                  this.streamingContent += data.chunk;
                } else if (data.done) {
                  // ストリーミング完了時の処理
                  this.messages.push({
                    role: 'assistant',
                    content: this.streamingContent,
                    timestamp: new Date().toISOString()
                  });
                  this.streamingContent = '';
                  await this.loadChats(); // チャット一覧を更新
                  break;
                } else if (data.error) {
                  throw new Error(data.error);
                }
              } catch (e) {
                console.error('Error parsing SSE data:', e);
              }
            }
          }
        }
      } catch (error) {
        console.error('Error:', error);
        this.messages.push({
          role: 'system',
          content: 'エラーが発生しました。もう一度お試しください。',
          timestamp: new Date().toISOString()
        });
      } finally {
        this.isStreaming = false;
        this.$nextTick(() => {
          this.$refs.chatInput.focus();
        });
      }
    }
  }
}
</script>

<style>
.page-container {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  position: relative;
}

.content-container {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  overflow-x: hidden;
}

.menu-toggle {
  position: fixed;
  left: 20px;
  top: 20px;
  z-index: 1001;
  padding: 8px 12px;
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 24px;
}

.options-toggle {
  position: fixed;
  right: 20px;
  top: 20px;
  z-index: 1001;
  padding: 8px 12px;
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 24px;
}

.chat-container {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  padding: 20px;
  box-sizing: border-box;
  width: 100%;
  max-width: 800px;
  padding-left: 60px;
}

.header {
  flex-shrink: 0;
}

.header h1 {
  margin: 0;
  padding-bottom: 20px;
}

/* ページ全体のスタイルリセット */
body {
  margin: 0;
  padding: 0;
  height: 100vh;
  overflow: hidden;
}
</style>