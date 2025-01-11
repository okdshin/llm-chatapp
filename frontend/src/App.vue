<template>
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
</template>

<script>
export default {
  data() {
    return {
      messages: [],
      userInput: ''
    }
  },
  mounted() {
    this.$refs.messageInput.focus();
    window.addEventListener('resize', this.adjustMessageContainerHeight);
    this.adjustMessageContainerHeight();
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.adjustMessageContainerHeight);
  },
  methods: {
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
      this.messages.push({
        role: 'user',
        content: message
      });
      this.userInput = '';

      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ message })
        });
        
        const data = await response.json();
        this.messages.push({
          role: 'assistant',
          content: data.response
        });

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
.chat-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 20px;
  box-sizing: border-box;
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