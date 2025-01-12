<template>
  <div class="input-container">
    <textarea ref="messageInput"
              v-model="inputValue" 
              @keyup.enter.prevent="handleSend" 
              :disabled="disabled"
              :placeholder="disabled ? '応答を生成中...' : 'Type your message...'"
              ></textarea>
  </div>
</template>

<script>
export default {
  name: 'ChatInput',
  
  props: {
    disabled: {
      type: Boolean,
      default: false
    }
  },

  data() {
    return {
      inputValue: ''
    }
  },

  methods: {
    handleSend() {
      if (this.disabled || !this.inputValue.trim()) return;
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

textarea:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}
</style>