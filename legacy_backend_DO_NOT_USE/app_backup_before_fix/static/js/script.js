// ============================================
// CONFIGURATION & STATE
// ============================================

const API_BASE_URL = window.location.origin;
const STORAGE_KEYS = {
    USER_ID: 'healer_nexus_user_id',
    CHAT_HISTORY: 'healer_nexus_chat_history',
    CURRENT_SERVICE: 'healer_nexus_current_service'
};

let userId = localStorage.getItem(STORAGE_KEYS.USER_ID) || Math.floor(10000 + Math.random() * 9000000);
let chatHistory = JSON.parse(localStorage.getItem(STORAGE_KEYS.CHAT_HISTORY) || '[]');
let currentService = localStorage.getItem(STORAGE_KEYS.CURRENT_SERVICE);
let isTyping = false;

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    localStorage.setItem(STORAGE_KEYS.USER_ID, userId);
    setupEventListeners();
    
    // Виправлено: викликаємо правильну функцію restoreChat()
    if (chatHistory.length > 0) {
        showChat();
        restoreChat(); 
        if (currentService) applyTheme(currentService);
    } else {
        showWelcome();
    }
    
    console.log(`🌟 Healer Nexus: User ${userId} initialized.`);
});

// ============================================
// UI NAVIGATION & THEMES
// ============================================

function showWelcome() {
    document.getElementById('welcomeScreen').classList.remove('hidden');
    document.getElementById('chatInterface').classList.add('hidden');
}

function showChat() {
    document.getElementById('welcomeScreen').classList.add('hidden');
    document.getElementById('chatInterface').classList.remove('hidden');
}

function applyTheme(service) {
    const body = document.body;
    // Очищуємо старі теми
    body.className = body.className.split(' ').filter(c => !c.startsWith('theme-')).join(' ');
    
    if (!service || service === 'unknown' || service === 'default') return;

    // Логіка мапінгу сервісів на теми
    let themeClass = `theme-${service}`;
    
    // Групування суміжних сервісів під спільні стилі
    if (service.includes('artist') || service === '3d_modeling') {
        themeClass = 'theme-creative_artist';
    } else if (service.includes('interior')) {
        themeClass = 'theme-interior_design';
    }
    
    body.classList.add(themeClass);
    currentService = service;
    localStorage.setItem(STORAGE_KEYS.CURRENT_SERVICE, service);
    console.log('🎨 Theme applied:', themeClass);
}

function startChat(category) {
    showChat();
    const categoryMessages = {
        'healer': 'Привіт! Мені потрібна допомога з медитацією та енергопрактиками.',
        'coach': 'Вітаю! Цікавить особистісний розвиток та коучинг.',
        'creative_artist': 'Доброго дня! Шукаю талановитого митця або ілюстратора для проєкту.',
        '3d_modeling': 'Привіт! Потрібна 3D візуалізація об\'єкту.',
        'interior_design': 'Добрий день! Потрібен дизайнер інтер\'єру для візуалізації оселі.',
        'web_development': 'Привіт! Хочу створити сучасний веб-сайт.'
    };
    
    const message = categoryMessages[category] || 'Привіт!';
    
    // Невелика затримка, щоб UI встиг переключитися
    setTimeout(() => {
        const input = document.getElementById('messageInput');
        if (input) {
            input.value = message;
            document.getElementById('chatForm').dispatchEvent(new Event('submit'));
        }
    }, 300);
}

// ============================================
// CHAT LOGIC
// ============================================

function setupEventListeners() {
    const form = document.getElementById('chatForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        
        if (!message || isTyping) return;
        input.value = '';

        addMessage('user', message);
        chatHistory.push({ role: 'user', text: message, timestamp: Date.now() });
        saveChat();

        showTypingIndicator();

        try {
            const response = await fetch(`${API_BASE_URL}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message, user_id: userId })
            });
            const data = await response.json();
            hideTypingIndicator();
            handleApiResponse(data);
        } catch (error) {
            hideTypingIndicator();
            console.error('Fetch error:', error);
            addMessage('assistant', '❌ Помилка з\'єднання. Перевірте сервер.', { isSafeMode: true });
        }
    });
}

function handleApiResponse(data) {
    applyTheme(data.detected_service);
    
    const aiMessage = {
        role: 'assistant',
        text: data.response,
        metadata: {
            detected_service: data.detected_service,
            top_specialists: data.top_specialists || [],
            smart_link: data.smart_link,
            isSafeMode: data.status === 'critical_safe_mode'
        }
    };

    chatHistory.push(aiMessage);
    saveChat();
    
    addMessage('assistant', data.response, aiMessage.metadata);
    
    if (data.top_specialists && data.top_specialists.length > 0) {
        setTimeout(() => {
            addSpecialistCards(data.top_specialists, data.smart_link);
        }, 800);
    }
}

// ============================================
// RENDERING
// ============================================

function addMessage(role, text, metadata = {}) {
    const container = document.getElementById('messagesContainer');
    const wrap = document.createElement('div');
    wrap.className = `flex ${role === 'user' ? 'justify-end' : 'justify-start'} mb-4`;
    
    const bubble = document.createElement('div');
    bubble.className = 'max-w-[85%] md:max-w-[70%] rounded-2xl px-4 py-3 shadow-sm border-2';
    
    if (role === 'user') {
        bubble.className += ' bg-indigo-600 text-white border-indigo-600'; // Використано класи замість var для надійності
        bubble.innerHTML = `<div class="flex gap-2"><span>👤</span><p>${escapeHtml(text)}</p></div>`;
    } else {
        bubble.style.background = 'var(--bg-secondary, white)';
        bubble.style.color = 'var(--text)';
        bubble.style.borderColor = 'var(--border)';
        const icon = metadata.isSafeMode ? '⚠️' : '🤖';
        bubble.innerHTML = `<div class="flex gap-2"><span>${icon}</span><p>${escapeHtml(text)}</p></div>`;
        
        if (!metadata.isSafeMode && metadata.detected_service && metadata.detected_service !== 'unknown') {
            const btn = document.createElement('button');
            btn.className = 'mt-2 text-xs underline opacity-50 hover:opacity-100 block';
            btn.textContent = '✗ Це не те';
            btn.onclick = () => {
                document.getElementById('messageInput').value = 'Це не те. Спробуй інший контекст.';
                document.getElementById('chatForm').dispatchEvent(new Event('submit'));
            };
            bubble.appendChild(btn);
        }
    }
    
    wrap.appendChild(bubble);
    container.appendChild(wrap);
    scrollToBottom();
}

function addSpecialistCards(specialists, smartLink) {
    const container = document.getElementById('messagesContainer');
    const scrollWrap = document.createElement('div');
    scrollWrap.className = 'flex gap-4 overflow-x-auto pb-4 no-scrollbar justify-start mt-2 w-full';
    
    specialists.forEach(spec => {
        const card = document.createElement('div');
        card.className = 'specialist-card min-w-[260px] p-4 rounded-xl border-2 bg-white shadow-md';
        card.style.borderColor = 'var(--border)';
        
        // Синхронізація з моделлю: delivery_method та hourly_rate
        const rate = spec.hourly_rate || spec.rate || '---';
        const deliveryLabel = {
            'human': '👤 Людина',
            'ai_assisted': '🤝 AI + Людина',
            'fully_ai': '🤖 AI Асистент'
        }[spec.delivery_method || spec.delivery] || '👤 Спеціаліст';

        card.innerHTML = `
            <div class="text-[10px] font-bold opacity-40 mb-1 uppercase tracking-wider">${deliveryLabel}</div>
            <div class="font-bold text-lg mb-1 text-gray-800">${escapeHtml(spec.name)}</div>
            <div class="text-xs h-10 overflow-hidden mb-3 text-gray-600">${escapeHtml(spec.specialty)}</div>
            <div class="flex justify-between items-center">
                <span class="font-bold text-indigo-600">${rate}₴/год</span>
                <button onclick="window.open('${smartLink}', '_blank')" 
                        class="px-4 py-2 bg-black text-white rounded-lg text-sm hover:scale-105 transition-transform">
                    Записатись
                </button>
            </div>
        `;
        scrollWrap.appendChild(card);
    });
    
    container.appendChild(scrollWrap);
    scrollToBottom();
}

// ============================================
// UTILS
// ============================================

function saveChat() { 
    localStorage.setItem(STORAGE_KEYS.CHAT_HISTORY, JSON.stringify(chatHistory)); 
}

function scrollToBottom() {
    const c = document.getElementById('messagesContainer');
    if (c) {
        setTimeout(() => { c.scrollTop = c.scrollHeight; }, 100);
    }
}

function showTypingIndicator() {
    isTyping = true;
    const container = document.getElementById('messagesContainer');
    const div = document.createElement('div');
    div.id = 'typingIndicator';
    div.className = 'flex justify-start mb-4';
    div.innerHTML = `<div class="p-3 rounded-2xl bg-gray-100 border-2 border-gray-200">
        <div class="flex gap-1"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>
    </div>`;
    container.appendChild(div);
    scrollToBottom();
}

function hideTypingIndicator() {
    isTyping = false;
    const el = document.getElementById('typingIndicator');
    if (el) el.remove();
}

function escapeHtml(t) {
    if (!t) return "";
    const d = document.createElement('div');
    d.textContent = t;
    return d.innerHTML;
}

function restoreChat() {
    const container = document.getElementById('messagesContainer');
    container.innerHTML = '';
    chatHistory.forEach(msg => {
        addMessage(msg.role, msg.text, msg.metadata || {});
        if (msg.metadata?.top_specialists?.length > 0) {
            addSpecialistCards(msg.metadata.top_specialists, msg.metadata.smart_link);
        }
    });
    scrollToBottom();
}
