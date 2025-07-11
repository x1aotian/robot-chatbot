let mediaRecorder;
let audioChunks = [];

document.getElementById("recordBtn").onclick = async () => {
  const recordBtn = document.getElementById("recordBtn");
  const statusText = document.getElementById("status");

  if (!mediaRecorder || mediaRecorder.state === "inactive") {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);

    mediaRecorder.onstart = () => {
      audioChunks = [];
      statusText.innerHTML = "🎙️ Recording... Speak now!";
      recordBtn.textContent = "⏹ Stop Recording";
    };

    mediaRecorder.ondataavailable = event => {
      audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
      statusText.innerHTML = "🔄 Processing...";
      recordBtn.textContent = "🎤 Start Recording";

      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
      const formData = new FormData();
      formData.append("audio", audioBlob);

      const mode = document.getElementById("mode").value;
      formData.append("mode", mode);

      try {
        const response = await fetch("http://localhost:5050/transcribe", {
          method: "POST",
          body: formData
        });

        if (!response.ok) {
          throw new Error(`Server error: ${response.statusText}`);
        }

        const result = await response.json();
        console.log("✅ Server responded:", result);

        // Display transcription and response
        statusText.innerHTML = `
          <div><b>📝 Transcription:</b> ${result.transcription}</div>
          <div><b>🤖 GPT Response:</b> ${result.message}</div>
        `;

        // Play the audio response
        const audio = new Audio(`http://localhost:5050${result.audio_url}`);
        audio.controls = true;
        statusText.appendChild(document.createElement("br"));
        statusText.appendChild(audio);

        // Try to play (for autoplay policies)
        try {
          await audio.play();
        } catch (e) {
          console.warn("Autoplay blocked:", e);
        }

      } catch (error) {
        console.error("❌ Fetch failed:", error);
        statusText.innerHTML = `<span style="color:red">❌ Error: ${error.message}</span>`;
      }
    };

    mediaRecorder.start();
  } else {
    mediaRecorder.stop();
  }
};

