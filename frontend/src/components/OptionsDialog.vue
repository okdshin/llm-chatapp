<template>
  <div v-if="isOpen" class="options-overlay" @click="$emit('close')">
    <div class="options-dialog" @click.stop>
      <div class="options-header">
        <h2>Options</h2>
        <button class="close-button" @click="$emit('close')">×</button>
      </div>
      <div class="options-content">
        <div class="option-item">
          <label>
            API Key
            <input type="password" v-model="localApiKey" placeholder="Enter your API key">
          </label>
        </div>
        <div class="option-item">
          <label>
            Model
            <select v-model="localModel">
              <option value="claude-3-opus">Claude 3 Opus</option>
              <option value="claude-3-sonnet">Claude 3 Sonnet</option>
              <option value="claude-3-haiku">Claude 3 Haiku</option>
            </select>
          </label>
        </div>
        <div class="option-item">
          <label>
            <input type="checkbox" v-model="localDarkMode">
            Dark Mode
          </label>
        </div>
      </div>
      <div class="options-footer">
        <button @click="saveOptions">Save</button>
        <button @click="$emit('close')">Cancel</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'OptionsDialog',
  
  props: {
    isOpen: {
      type: Boolean,
      required: true
    },
    apiKey: {
      type: String,
      required: true
    },
    selectedModel: {
      type: String,
      required: true
    },
    darkMode: {
      type: Boolean,
      required: true
    }
  },

  data() {
    return {
      localApiKey: this.apiKey,
      localModel: this.selectedModel,
      localDarkMode: this.darkMode
    }
  },

  methods: {
    saveOptions() {
      this.$emit('save', {
        apiKey: this.localApiKey,
        selectedModel: this.localModel,
        darkMode: this.localDarkMode
      });
    }
  },

  watch: {
    isOpen(newValue) {
      if (newValue) {
        this.localApiKey = this.apiKey;
        this.localModel = this.selectedModel;
        this.localDarkMode = this.darkMode;
      }
    }
  }
}
</script>

<style scoped>
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
</style>