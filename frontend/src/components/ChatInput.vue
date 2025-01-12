<template>
  <div class="input-container">
    <textarea ref="messageInput"
              v-model="inputValue" 
              @keyup.enter.prevent="handleSend" 
              placeholder="Type your message..."></textarea>
  </div>
</template>

<script>
export default {
  name: 'ChatInput',
  
  data() {
    return {
      inputValue: ''
    }
  },

  methods: {
    handleSend() {
      if (!this.inputValue.trim()) return;
      this.$emit('send', this.inputValue.trim());
      this.inputValue = '';
    },

    focus() {
      this.$refs.messageInput.focus();
    }
  }
}
</script>

<style scoped>
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
</style>