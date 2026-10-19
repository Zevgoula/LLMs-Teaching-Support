/* Audio recorder: capture mic, draw waveform, encode WAV, save, start pipeline. */



// ---------- State ----------
let isRecording = false;
let audioContext = null;
let audioStream = null;
let scriptProcessor = null;
let analyser = null;
let animationId = null;
let audioBuffers = [];
let recordedWavBlob = null;

// ---------- Elements ----------
const recordBtn = document.getElementById('recordBtn');
const saveBtn = document.getElementById('saveBtn');
const audioPlayback = document.getElementById('audioPlayback');
const statusMessage = document.getElementById('statusMessage');
const canvas = document.getElementById('waveformCanvas');
const ctx = canvas.getContext('2d');

drawBaseline();

/* Shared across all pages. */

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.classList.toggle('collapsed');
}

// ---------- Canvas drawing ----------
function drawBaseline() {
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.3)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, canvas.height / 2);
    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.stroke();
}

function renderWave() {
    if (!isRecording || !analyser) return;

    animationId = requestAnimationFrame(renderWave);

    const bufferLength = analyser.frequencyBinCount;
    const timeData = new Uint8Array(bufferLength);
    analyser.getByteTimeDomainData(timeData);

    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const gradient = ctx.createLinearGradient(0, 0, canvas.width, 0);
    gradient.addColorStop(0, '#38bdf8');
    gradient.addColorStop(0.5, '#818cf8');
    gradient.addColorStop(1, '#c084fc');

    ctx.lineWidth = 2.5;
    ctx.strokeStyle = gradient;
    ctx.shadowBlur = 8;
    ctx.shadowColor = '#38bdf8';
    ctx.beginPath();

    const sliceWidth = canvas.width / bufferLength;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
        const v = timeData[i] / 128.0;
        const y = (v * canvas.height) / 2;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
        x += sliceWidth;
    }

    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.stroke();
    ctx.shadowBlur = 0;
}

// ---------- Recording ----------
async function toggleRecording() {
    if (isRecording) {
        stopRecording();
    } else {
        await startRecording();
    }
}

async function startRecording() {
    try {
        statusMessage.innerText = 'Accessing microphone...';

        audioStream = await navigator.mediaDevices.getUserMedia({
            audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true }
        });

        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        if (audioContext.state === 'suspended') {
            await audioContext.resume();
        }

        const source = audioContext.createMediaStreamSource(audioStream);

        // Live visualizer
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 2048;
        source.connect(analyser);

        // Raw PCM capture
        scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
        audioBuffers = [];

        scriptProcessor.onaudioprocess = (e) => {
            if (!isRecording) return;
            audioBuffers.push(new Float32Array(e.inputBuffer.getChannelData(0)));
        };

        source.connect(scriptProcessor);
        scriptProcessor.connect(audioContext.destination);

        isRecording = true;
        recordBtn.innerText = '■ Stop Recording';
        recordBtn.classList.add('recording');
        saveBtn.disabled = true;
        audioPlayback.style.display = 'none';
        statusMessage.innerText = 'Recording... speak now.';

        renderWave();
    } catch (err) {
        console.error(err);
        statusMessage.innerText = 'Microphone error: ' + err.message;
    }
}

function stopRecording() {
    isRecording = false;

    if (animationId) cancelAnimationFrame(animationId);
    if (scriptProcessor) scriptProcessor.disconnect();
    if (audioStream) audioStream.getTracks().forEach(t => t.stop());

    const sampleRate = audioContext.sampleRate;
    if (audioContext && audioContext.state !== 'closed') audioContext.close();

    recordBtn.innerText = '● Start Recording';
    recordBtn.classList.remove('recording');
    drawBaseline();

    recordedWavBlob = exportWAV(audioBuffers, sampleRate);

    if (recordedWavBlob.size < 100) {
        statusMessage.innerText = 'No audio detected. Please check microphone settings.';
        return;
    }

    audioPlayback.src = URL.createObjectURL(recordedWavBlob);
    audioPlayback.style.display = 'block';
    audioPlayback.load();

    saveBtn.disabled = false;
    statusMessage.innerText =
        `Recording ready (${(recordedWavBlob.size / 1024).toFixed(1)} KB). Click 'Save Recording' to keep it.`;
}

// ---------- WAV encoding ----------
function exportWAV(buffers, sampleRate) {
    let totalLength = 0;
    for (const b of buffers) totalLength += b.length;

    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const b of buffers) {
        merged.set(b, offset);
        offset += b.length;
    }

    const wavBuffer = new ArrayBuffer(44 + merged.length * 2);
    const view = new DataView(wavBuffer);

    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + merged.length * 2, true);
    writeString(view, 8, 'WAVE');

    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);              // PCM
    view.setUint16(22, 1, true);              // mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);             // 16-bit

    writeString(view, 36, 'data');
    view.setUint32(40, merged.length * 2, true);

    let index = 44;
    for (let i = 0; i < merged.length; i++, index += 2) {
        const s = Math.max(-1, Math.min(1, merged[i]));
        view.setInt16(index, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }

    return new Blob([view], { type: 'audio/wav' });
}

function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}

// ---------- Saving + pipeline ----------
async function startPipeline(filename) {
    statusMessage.innerText = `✅ Saved to project: recordings/${filename}. Starting docu_video_pipeline...`;
    try {
        const res = await fetch('/run_docu_video_pipeline', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename })
        });
        const data = await res.json().catch(() => ({}));

        if (!res.ok || data.status !== 'success') {
            console.error('Pipeline error:', data);
            statusMessage.innerText =
                `⚠️ Audio saved, but the pipeline could not start: ${data.message || 'Unknown error'}`;
        } else {
            statusMessage.innerText =
                `✅ Saved to project: recordings/${filename} and pipeline started successfully.`;
        }
    } catch (err) {
        console.error('Pipeline request error:', err);
        statusMessage.innerText = '⚠️ Audio saved, but the pipeline request failed.';
    }
}

async function saveAudio() {
    if (!recordedWavBlob) return;

    saveBtn.disabled = true;
    statusMessage.innerText = 'Saving to project...';

    const fd = new FormData();
    fd.append('audio_file', recordedWavBlob, 'recording.wav');

    try {
        const res = await fetch('/save_recording', { method: 'POST', body: fd });

        if (!res.ok) {
            console.error('Server error response:', await res.text());
            statusMessage.innerText =
                `Error (${res.status}): Make sure you restarted app.py after saving the changes.`;
            return;
        }

        const data = await res.json();
        if (data.status === 'success') {
            await startPipeline(data.filename);
        } else {
            statusMessage.innerText = `❌ Error: ${data.message || 'Could not save file'}`;
        }
    } catch (err) {
        console.error('Save error:', err);
        statusMessage.innerText = 'Network error: ' + err.message;
    } finally {
        saveBtn.disabled = false;
    }
}