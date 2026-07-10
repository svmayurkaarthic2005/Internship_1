/**
 * Chat Storage Module
 * Handles sessionStorage for chat history
 */

const STORAGE_KEY_CHAT_HISTORY = 'sis_chat_history';
const STORAGE_KEY_SESSION_ID = 'sis_current_session_id';
const MAX_HISTORY_MESSAGES = 50; // Keep last 50 messages

/**
 * Save chat history to sessionStorage
 */
function saveChatHistoryToStorage(history) {
    try {
        // Keep only last MAX_HISTORY_MESSAGES
        const trimmedHistory = history.slice(-MAX_HISTORY_MESSAGES);
        sessionStorage.setItem(STORAGE_KEY_CHAT_HISTORY, JSON.stringify(trimmedHistory));
        console.log(`💾 Saved ${trimmedHistory.length} messages to sessionStorage`);
    } catch (error) {
        console.error('Error saving chat history:', error);
    }
}

/**
 * Load chat history from sessionStorage
 */
function loadChatHistoryFromStorage() {
    try {
        const stored = sessionStorage.getItem(STORAGE_KEY_CHAT_HISTORY);
        if (stored) {
            const history = JSON.parse(stored);
            console.log(`📂 Loaded ${history.length} messages from sessionStorage`);
            return history;
        }
    } catch (error) {
        console.error('Error loading chat history:', error);
    }
    return [];
}

/**
 * Add message to chat history and save to storage
 */
function addMessageToHistory(role, content, language = 'auto') {
    const message = {
        role: role,
        content: content,
        language: language,
        timestamp: new Date().toISOString()
    };
    
    // Get current history
    const history = loadChatHistoryFromStorage();
    history.push(message);
    
    // Save updated history
    saveChatHistoryToStorage(history);
    
    return message;
}

/**
 * Clear chat history from sessionStorage
 */
function clearChatHistory() {
    try {
        sessionStorage.removeItem(STORAGE_KEY_CHAT_HISTORY);
        console.log('🗑️ Cleared chat history from sessionStorage');
    } catch (error) {
        console.error('Error clearing chat history:', error);
    }
}

/**
 * Save current session ID
 */
function saveSessionId(sessionId) {
    try {
        sessionStorage.setItem(STORAGE_KEY_SESSION_ID, sessionId);
        console.log('💾 Saved session ID:', sessionId);
    } catch (error) {
        console.error('Error saving session ID:', error);
    }
}

/**
 * Load current session ID
 */
function loadSessionId() {
    try {
        const sessionId = sessionStorage.getItem(STORAGE_KEY_SESSION_ID);
        if (sessionId) {
            console.log('📂 Loaded session ID:', sessionId);
            return sessionId;
        }
    } catch (error) {
        console.error('Error loading session ID:', error);
    }
    return null;
}

/**
 * Get chat history formatted for API (last N messages only)
 */
function getChatHistoryForAPI(limit = 10) {
    const history = loadChatHistoryFromStorage();
    // Return last N messages for context
    return history.slice(-limit);
}

// Export functions for use in chat.js
window.chatStorage = {
    save: saveChatHistoryToStorage,
    load: loadChatHistoryFromStorage,
    addMessage: addMessageToHistory,
    clear: clearChatHistory,
    saveSessionId: saveSessionId,
    loadSessionId: loadSessionId,
    getForAPI: getChatHistoryForAPI
};
