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
      <!-- ... 以前のサイドメニューの内容 ... -->
    </div>

    <!-- メインコンテンツ -->
    <div class="content-container">
      <!-- ... 以前のメインコンテンツ ... -->
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

    <div v-if="isMenuOpen" class="overlay" @click="toggleMenu"></div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      // ... 以前のdata ...
      isOptionsOpen: false,
      apiKey: '',
      selectedModel: 'claude-3-opus',
      darkMode: false
    }
  },
  methods: {
    // ... 以前のmethods ...
    toggleOptions() {
      this.isOptionsOpen = !this.isOptionsOpen;
    },
    closeOptions() {
      this.isOptionsOpen = false;
    },
    saveOptions() {
      // オプションを保存する処理をここに実装
      localStorage.setItem('apiKey', this.apiKey);
      localStorage.setItem('selectedModel', this.selectedModel);
      localStorage.setItem('darkMode', this.darkMode);
      this.closeOptions();
    },
    loadOptions() {
      this.apiKey = localStorage.getItem('apiKey') || '';
      this.selectedModel = localStorage.getItem('selectedModel') || 'claude-3-opus';
      this.darkMode = localStorage.getItem('darkMode') === 'true';
    }
  },
  mounted() {
    // ... 以前のmounted処理 ...
    this.loadOptions();
  }
}
</script>

<style>
/* ... 以前のスタイル ... */

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