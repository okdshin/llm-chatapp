<template>
  <div class="chat-container">
    <h1>Simple Chat</h1>
    
    <div class="messages" ref="messageContainer">
      <div v-for="(message, index) in messages" :key="index" 
           :class="['message', message.role]">
        <strong>{{ message.role === 'user' ? 'You' : 'Assistant' }}:</strong>
        <p>{{ message.content }}</p>
      </div>
    </div>

    <div class="input-container">
      <textarea v-model="userInput" 
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
  methods: {
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
      } catch (error) {
        console.error('Error:', error);
      }
    }
  },
  updated() {
    // Scroll to bottom when new messages arrive
    this.$nextTick(() => {
      const container = this.$refs.messageContainer;
      container.scrollTop = container.scrollHeight;
    });
  }
}
</script>

<style>
.chat-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.messages {
  height: 400px;
  overflow-y: auto;
  border: 1px solid #ccc;
  padding: 10px;
  margin-bottom: 20px;
}

.message {
  margin-bottom: 10px;
  padding: 10px;
  border-radius: 4px;
}

.message.user {
  background-color: #f0f0f0;
}

.message.assistant {
  background-color: #e3f2fd;
}

.input-container {
  display: flex;
  gap: 10px;
}

textarea {
  flex-grow: 1;
  height: 60px;
  resize: none;
}

button {
  align-self: flex-end;
}
</style>