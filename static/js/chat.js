/* Landing page: sidebar, PDF upload, and chat with the tutor. */

const pdfInput = document.getElementById('pdfInput');
const statusText = document.getElementById('status-text');
const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('userInput');

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('collapsed');
}

async function uploadPDF() {
    if (pdfInput.files.length === 0) {
        alert('Please select a file first.');
        return;
    }

    statusText.className = '';
    statusText.innerText = 'Uploading… please wait.';

    const formData = new FormData();
    formData.append('pdf_file', pdfInput.files[0]);

    try {
        const response = await fetch('/upload', { method: 'POST', body: formData });
        const result = await response.json();

        if (result.status === 'success') {
            statusText.innerText = '✓ Ready! Start chatting.';
            statusText.className = 'success';
        } else {
            statusText.innerText = 'Error: ' + result.error;
            statusText.className = 'error';
        }
    } catch (err) {
        statusText.innerText = 'Network error: ' + err.message;
        statusText.className = 'error';
    }
}

function appendMessage(text, className) {
    const div = document.createElement('div');
    div.className = 'msg ' + className;
    div.textContent = text;
    chatBox.appendChild(div);
}

function appendHtml(html, className) {
    const div = document.createElement('div');
    div.className = 'msg ' + className;
    div.innerHTML = html;
    chatBox.appendChild(div);
}

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    appendMessage(text, 'user-msg');
    userInput.value = '';

    const typingId = 'typing-' + Date.now();
    chatBox.insertAdjacentHTML(
        'beforeend',
        `<div class="typing-indicator" id="${typingId}"><span></span><span></span><span></span></div>`
    );
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });
        const result = await response.json();

        document.getElementById(typingId)?.remove();

        if (result.error) {
            appendMessage('⚠ ' + result.error, 'ai-msg error-msg');
        } else {
            appendHtml(marked.parse(result.reply), 'ai-msg');
        }
    } catch (err) {
        document.getElementById(typingId)?.remove();
        appendMessage('⚠ Network error: ' + err.message, 'ai-msg error-msg');
    }

    chatBox.scrollTop = chatBox.scrollHeight;
}

userInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});