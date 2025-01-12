<template>
  <div class="messages" ref="messageContainer">
    <div v-for="(message, index) in messages" 
        :key="index" 
        :class="['message-wrapper', message.role]">
      <div class="message">
        <p>{{ message.content }}</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ChatMessages',
  
  props: {
    messages: {
      type: Array,
      required: true
    }
  },

  methods: {
    scrollToBottom() {
      this.$refs.messageContainer.scrollTop = this.$refs.messageContainer.scrollHeight;
    }
  },

  updated() {
    this.$nextTick(this.scrollToBottom);
  }
}
</script>

<style scoped>
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

.system .message {
  background-color: #ffe0e0;
  color: #d32f2f;
  width: 100%;
  text-align: center;
}
</style>