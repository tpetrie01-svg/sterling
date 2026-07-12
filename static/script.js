const log = document.getElementById("log");
const promptInput = document.getElementById("prompt");
const player = document.getElementById("player");
let recorder, chunks = [];

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

promptInput.addEventListener("keydown", async (e) => {
    if (e.key !== "Enter" || !promptInput.value.trim()) return;

    const prompt = promptInput.value.trim();
    promptInput.value = "";
    send(prompt);
});

async function send(prompt) {
    promptInput.disabled = true;

    log.innerHTML += `<div class="you">You: ${prompt}</div>`;

    const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt })
    });
    const data = await res.json();

    if (data.error) {
        log.innerHTML += `<div>Error: ${data.error}</div>`;
        promptInput.disabled = false;
        return;
    }

    // Start audio and word-by-word typing together
    player.src = data.audio;
    player.play();

    const words = data.reply.split(" ");
    const delay = (data.duration * 1000) / words.length;

    const sterlingLine = document.createElement("div");
    sterlingLine.className = "sterling";
    sterlingLine.textContent = "Sterling: ";
    log.appendChild(sterlingLine);

    for (let i = 0; i < words.length; i++) {
        sterlingLine.textContent += (i > 0 ? " " : "") + words[i];
        log.scrollTop = log.scrollHeight;
        await new Promise(r => setTimeout(r, delay));
    }

    promptInput.disabled = false;
    promptInput.focus();
}