async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value;
    if (!message) return;

    // Додаємо повідомлення користувача в інтерфейс
    appendMessage('user', message);
    input.value = '';

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        });

        const data = await response.json();
        
        if (response.status === 200) {
            appendMessage('assistant', data.response);
            // Якщо бекенд повертає роль, можемо її підсвітити
            console.log("Детектована роль:", data.detected_role);
        } else {
            appendMessage('assistant', "❌ " + (data.detail || "Помилка лімітів"));
        }
    } catch (error) {
        appendMessage('assistant', "🌐 Помилка з'єднання з сервером");
    }
}

function appendMessage(role, text) {
    const container = document.getElementById('chat-container');
    const msgDiv = document.createElement('div');
    msgDiv.className = role === 'user' ? 'user-msg' : 'ai-msg';
    msgDiv.innerText = text;
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
}
