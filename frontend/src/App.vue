<template>
  <div class="page-container">
    <button class="menu-toggle" @click="toggleMenu">
      {{ isMenuOpen ? '×' : '☰' }}
    </button>

    <!-- オプションボタン -->
    <button class="options-toggle" @click="toggleOptions">
      ⚙️
    </button>

    <!-- サイドメニュー -->
    <div :class="['side-menu', { 'closed': !isMenuOpen }]">
      <div class="menu-header">
        <h2>Chats</h2>
        <button @click="createNewChat" class="new-chat-btn">New Chat</button>
      </div>
      <div class="chat-list">
        <div v-for="chat in chats" 
             :key="chat.id" 
             :class="['chat-item', { active: currentChatId === chat.id }]"
             @click="loadChat(chat.id)">
          <p class="chat-preview">{{ chat.preview }}</p>
          <small class="chat-date">{{ formatDate(chat.created_at) }}</small>
        </div>
      </div>
    </div>

    <!-- メインコンテンツ -->
    <div class="content-container">
      <div class="chat-container">
        <div class="header">
          <h1>Simple Chat</h1>
        </div>
        
        <div class="messages" ref="messageContainer">
          <div v-for="(message, index) in messages" :key="index" 
              :class="['message-wrapper', message.role]">
            <div class="message">
              <p>{{ message.content }}</p>
            </div>
          </div>
        </div>

        <div class="input-container">
          <textarea ref="messageInput"
                    v-model="userInput" 
                    @keyup.enter.prevent="sendMessage" 
                    placeholder="Type your message..."></textarea>
        </div>
      </div>
    </div>

    <!-- オプションダイアログ -->
    <div v-if="isOptionsOpen" class="options-overlay" @click="closeOptions">
      <div class="options-dialog" @click.stop>
        <div class="options-header">
          <h2>Options</h2>
          <button class="close-button" @click="closeOptions">×</button>
        </div>
        <div class="options-content">
          <div class="option-item">
            <label>
              API Key
              <input type="password" v-model="apiKey" placeholder="Enter your API key">
            </label>
          </div>
          <div class="option-item">
            <label>
              Model
              <select v-model="selectedModel">
                <option value="claude-3-opus">Claude 3 Opus</option>
                <option value="claude-3-sonnet">Claude 3 Sonnet</option>
                <option value="claude-3-haiku">Claude 3 Haiku</option>
              </select>
            </label>
          </div>
          <div class="option-item">
            <label>
              <input type="checkbox" v-model="darkMode">
              Dark Mode
            </label>
          </div>
        </div>
        <div class="options-footer">
          <button @click="saveOptions">Save</button>
          <button @click="closeOptions">Cancel</button>
        </div>
      </div>
    </div>

    <!-- メニューオーバーレイ -->
    <div v-if="isMenuOpen" class="overlay" @click="toggleMenu"></div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      messages: [],
      userInput: '',
      chats: [],
      currentChatId: null,
      isMenuOpen: false,
      isOptionsOpen: false,
      apiKey: '',
      selectedModel: 'claude-3-opus',
      darkMode: false
    }
  },
  async mounted() {
    this.$refs.messageInput.focus();
    window.addEventListener('resize', this.adjustMessageContainerHeight);
    this.adjustMessageContainerHeight();
    await this.loadChats();
    if (!this.currentChatId) {
      await this.createNewChat();
    }
    this.loadOptions();
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
    saveOptions() {
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
    formatDate(dateStr) {
      return new Date(dateStr).toLocaleString();
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
      const messageContainer = this.$refs.messageContainer;
      messageContainer.style.height = `${windowHeight - header - input - 40}px`;
    },
    async sendMessage() {
      if (!this.userInput.trim()) return;
      
      const message = this.userInput;
      this.userInput = '';

      try {
        const response = await fetch(`/api/chats/${this.currentChatId}/messages`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ message })
        });
        
        const chatData = await response.json();
        await this.loadChat(this.currentChatId);
        await this.loadChats();

        this.$nextTick(() => {
          this.$refs.messageInput.focus();
        });
      } catch (error) {
        console.error('Error:', error);
      }
    }
  },
  updated() {
    this.$nextTick(() => {
      const container = this.$refs.messageContainer;
      container.scrollTop = container.scrollHeight;
    });
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

.side-menu {
  position: fixed;
  left: 0;
  top: 0;
  width: 260px;
  height: 100vh;
  background-color: #f8f9fa;
  display: flex;
  flex-direction: column;
  z-index: 1000;
  transform: translateX(-100%);
  transition: transform 0.3s ease;
  box-shadow: 2px 0 5px rgba(0,0,0,0.1);
}

.side-menu.closed {
  transform: translateX(-100%);
}

.side-menu:not(.closed) {
  transform: translateX(0);
}

.overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 999;
}

.menu-header {
  padding: 20px;
  border-bottom: 1px solid #dee2e6;
  margin-top: 40px;
}

.menu-header h2 {
  margin: 0;
  margin-bottom: 10px;
}

.new-chat-btn {
  width: 100%;
  padding: 8px;
}

.chat-list {
  flex-grow: 1;
  overflow-y: auto;
  padding: 10px;
}

.chat-item {
  padding: 10px;
  margin-bottom: 5px;
  border-radius: 4px;
  cursor: pointer;
}

.chat-item:hover {
  background-color: #e9ecef;
}

.chat-item.active {
  background-color: #e3f2fd;
}

.chat-preview {
  margin: 0;
  font-size: 0.9em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-date {
  color: #6c757d;
  font-size: 0.8em;
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

.messages {
  flex-grow: 1;
  overflow-y: auto;
  padding: 10px;
  margin-bottom: 20px;
}

.message-wrapper {
  width: 100%;
  display: flex;
  margin-bottom: 10px;
}

.message {
  padding: 10px;
  border-radius: 4px;
  word-wrap: break-word;
  width: 100%;
  box-sizing: border-box;
}

.message p {
  margin: 0;
  white-space: pre-wrap;
}

.user .message {
  background-color: #f0f0f0;
  width: fit-content;
  max-width: 100%;
}

.assistant .message {
  background-color: #e3f2fd;
  width: 100%;
}

.input-container {
  flex-shrink: 0;
  margin-top: 10px;
}

textarea {
  width: 100%;
  height: 60px;
  padding: 10px;
  border-radius: 4px;
  resize: none;
  box-sizing: border-box;
}

/* オプションダイアログのスタイル */
.options-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1002;
}

.options-dialog {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.options-header {
  padding: 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.options-header h2 {
  margin: 0;
}

.close-button {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  padding: 0 8px;
}

.options-content {
  padding: 20px;
}

.option-item {
  margin-bottom: 20px;
}

.option-item label {
  display: block;
  margin-bottom: 8px;
}

.option-item input[type="password"],
.option-item select {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-top: 4px;
}

.options-footer {
  padding: 20px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.options-footer button {
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}

/* ページ全体のスタイルリセット */
body {
  margin: 0;
  padding: 0;
  height: 100vh;
  overflow: hidden;
}
</style>