<template>
  <div class="page-container">
    <!-- メニューのトグルボタン -->
    <button class="menu-toggle" @click="toggleMenu">
      {{ isMenuOpen ? '×' : '☰' }}
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

    <!-- メインコンテンツのセンタリングコンテナ -->
    <div class="content-container">
      <!-- メインチャットエリア -->
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
                    @keyup.enter="sendMessage" 
                    placeholder="Type your message..."></textarea>
          <button @click="sendMessage">Send</button>
        </div>
      </div>
    </div>

    <!-- オーバーレイ背景 -->
    <div v-if="isMenuOpen" class="overlay" @click="toggleMenu"></div>
  </div>
</template>

<script>
// scriptの部分は変更なし
export default {
  data() {
    return {
      messages: [],
      userInput: '',
      chats: [],
      currentChatId: null,
      isMenuOpen: false
    }
  },
  // 以下のメソッドは同じなので省略
  mounted() { ... },
  beforeDestroy() { ... },
  methods: { ... },
  updated() { ... }
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
</style>