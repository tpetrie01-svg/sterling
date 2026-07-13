const log = document.getElementById("log");
const promptInput = document.getElementById("prompt");
const player = document.getElementById("player");
let recorder, chunks = [];

const SPINNER_FRAMES = ["|", "/", "-", "\\"];
let lastContext = { used: null, max: null };

function formatContext() {
    if (lastContext.used === null) return "";
    return lastContext.max
        ? `[ctx ${lastContext.used}/${lastContext.max}]`
        : `[ctx ${lastContext.used}]`;
}

function escapeHtml(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function renderMarkdown(text) {
    let html = escapeHtml(text);

    html = html.replace(/```(?:\w+\n)?([\s\S]*?)```/g, (_, code) => `<pre><code>${code}</code></pre>`);
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    html = html.replace(/\*\*\*([^*]+)\*\*\*/g, "<strong><em>$1</em></strong>");
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/__([^_]+)__/g, "<strong>$1</strong>");
    html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    html = html.replace(/(?<!\w)_([^_]+)_(?!\w)/g, "<em>$1</em>");
    html = html.replace(/~~([^~]+)~~/g, "<del>$1</del>");
    html = html.replace(/^###### (.*)$/gm, "<h6>$1</h6>");
    html = html.replace(/^##### (.*)$/gm, "<h5>$1</h5>");
    html = html.replace(/^#### (.*)$/gm, "<h4>$1</h4>");
    html = html.replace(/^### (.*)$/gm, "<h3>$1</h3>");
    html = html.replace(/^## (.*)$/gm, "<h2>$1</h2>");
    html = html.replace(/^# (.*)$/gm, "<h1>$1</h1>");
    html = html.replace(/^\s*[-*+] (.*)$/gm, "• $1");
    html = html.replace(/\n/g, "<br>");
    return html;
}

mic.addEventListener("click", async () => {
    if (recorder?.state === "recording") { recorder.stop(); return; }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recorder = new MediaRecorder(stream);
    chunks = [];
    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        mic.textContent = "🎤";
        const fd = new FormData();
        fd.append("audio", new Blob(chunks, { type: "audio/webm" }), "clip.webm");
        const res = await fetch("/stt", { method: "POST", body: fd });
        const { text, error } = await res.json();
        if (text) send(text);
        else log.innerHTML += `<div>STT error: ${error}</div>`;
    };
    recorder.start();
    mic.textContent = "⏹";
});

reset.addEventListener("click", async () => {
    await fetch("/reset", { method: "POST" });
    log.innerHTML = "";
});

promptInput.addEventListener("keydown", async (e) => {
    if (e.key !== "Enter" || !promptInput.value.trim()) return;

    const prompt = promptInput.value.trim();
    promptInput.value = "";
    send(prompt);
});

async function send(prompt) {
    promptInput.disabled = true;

    log.innerHTML += `<div class="you">You: ${prompt}</div>`;

    const thinkingLine = document.createElement("div");
    thinkingLine.className = "thinking";
    log.appendChild(thinkingLine);
    log.scrollTop = log.scrollHeight;

    let frame = 0;
    const renderThinking = () => {
        thinkingLine.innerHTML =
            `<span class="spinner">${SPINNER_FRAMES[frame % SPINNER_FRAMES.length]}</span> ` +
            `<span class="ctx">${formatContext()}</span>`;
        frame++;
    };
    renderThinking();
    const spin = setInterval(renderThinking, 120);

    let data;
    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt })
        });
        data = await res.json();
    } finally {
        clearInterval(spin);
        thinkingLine.remove();
    }

    if (data.error) {
        log.innerHTML += `<div>Error: ${data.error}</div>`;
        promptInput.disabled = false;
        return;
    }

    if (data.context_used !== undefined) {
        lastContext = { used: data.context_used, max: data.context_max };
    }

    // Start audio and word-by-word typing together
    player.src = data.audio;
    player.play();

    const words = data.reply.split(" ");
    const delay = (data.duration * 1000) / words.length;

    const sterlingLine = document.createElement("div");
    sterlingLine.className = "sterling";
    log.appendChild(sterlingLine);

    let shown = "";
    for (let i = 0; i < words.length; i++) {
        shown += (i > 0 ? " " : "") + words[i];
        sterlingLine.innerHTML = "Sterling: " + renderMarkdown(shown);
        log.scrollTop = log.scrollHeight;
        await new Promise(r => setTimeout(r, delay));
    }

    sterlingLine.innerHTML += ` <span class="ctx">${formatContext()}</span>`;

    promptInput.disabled = false;
    promptInput.focus();
}