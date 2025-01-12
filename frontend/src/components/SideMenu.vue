<template>
  <div>
    <div :class="['side-menu', { 'closed': !isOpen }]">
      <div class="menu-header">
        <h2>Chats</h2>
        <button @click="$emit('new-chat')" class="new-chat-btn">New Chat</button>
      </div>
      <div class="chat-list">
        <div v-for="chat in chats" 
             :key="chat.id" 
             :class="['chat-item', { active: currentChatId === chat.id }]"
             @click="$emit('select-chat', chat.id)">
          <p class="chat-preview">{{ chat.preview }}</p>
          <small class="chat-date">{{ formatDate(chat.created_at) }}</small>
        </div>
      </div>
    </div>
    <div v-if="isOpen" class="overlay" @click="$emit('toggle')"></div>
  </div>
</template>

<script>
export default {
  name: 'SideMenu',
  
  props: {
    isOpen: {
      type: Boolean,
      required: true
    },
    chats: {
      type: Array,
      required: true
    },
    currentChatId: {
      type: String,
      required: true
    }
  },

  methods: {
    formatDate(dateStr) {
      return new Date(dateStr).toLocaleString();
    }
  }
}
</script>

<style scoped>
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
</style>