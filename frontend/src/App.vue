<template>
  <div class="page-container">
    <!-- サイドメニューのトグルボタン -->
    <button class="menu-toggle" @click="toggleMenu">
      {{ isMenuOpen ? '≪' : '≫' }}
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

    <!-- メインチャットエリア -->
    <div :class="['chat-container', { 'menu-closed': !isMenuOpen }]">
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
                  @keyup.enter="sendMessage" 
                  placeholder="Type your message..."></textarea>
        <button @click="sendMessage">Send</button>
      </div>
    </div>
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
      isMenuOpen: true
    }
  },
  async mounted() {
    this.$refs.messageInput.focus();
    window.addEventListener('resize', this.handleResize);
    this.handleResize();
    await this.loadChats();
    if (!this.currentChatId) {
      await this.createNewChat();
    }
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.handleResize);
  },
  methods: {
    handleResize() {
      this.adjustMessageContainerHeight();
      // 画面幅が狭い場合は自動的にメニューを閉じる
      if (window.innerWidth < 768) {
        this.isMenuOpen = false;
      }
    },
    toggleMenu() {
      this.isMenuOpen = !this.isMenuOpen;
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
      // モバイル表示の場合は自動的にメニューを閉じる
      if (window.innerWidth < 768) {
        this.isMenuOpen = false;
      }
    },
    async loadChat(chatId) {
      try {
        const response = await fetch(`/api/chats/${chatId}`);
        const chatData = await response.json();
        this.messages = chatData.messages;
        this.currentChatId = chatId;
        // モバイル表示の場合は自動的にメニューを閉じる
        if (window.innerWidth < 768) {
          this.isMenuOpen = false;
        }
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

.menu-toggle {
  position: fixed;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 1000;
  padding: 10px 5px;
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-left: none;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.3s;
}

.menu-toggle:hover {
  opacity: 1;
}

.side-menu {
  width: 260px;
  background-color: #f8f9fa;
  border-right: 1px solid #dee2e6;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: transform 0.3s ease;
  position: relative;
  z-index: 100;
}

.side-menu.closed {
  transform: translateX(-100%);
}

.menu-header {
  padding: 20px;
  border-bottom: 1px solid #dee2e6;
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
  transition: margin-left 0.3s ease;
  width: 100%;
}

.chat-container.menu-closed {
  margin-left: 0;
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
}

.message p {
  margin: 0;
  white-space: pre-wrap;
}

.user .message {
  background-color: #f0f0f0;
  width: fit-content;
  max-width: 80%;
}

.assistant .message {
  background-color: #e3f2fd;
  width: 80%;
}

.input-container {
  flex-shrink: 0;
  display: flex;
  gap: 10px;
  padding-top: 10px;
}

textarea {
  flex-grow: 1;
  height: 60px;
  resize: none;
}

button {
  align-self: flex-end;
}

/* ページ全体のスタイルリセット */
body {
  margin: 0;
  padding: 0;
  height: 100vh;
  overflow: hidden;
}

@media (max-width: 768px) {
  .menu-toggle {
    padding: 15px 8px;
  }
  
  .side-menu {
    position: fixed;
    height: 100vh;
    box-shadow: 2px 0 5px rgba(0,0,0,0.1);
  }
}
</style>