const video = document.querySelector("#video");
const fileInput = document.querySelector("#video-file");
const cameraStart = document.querySelector("#camera-start");
const cameraStop = document.querySelector("#camera-stop");
const analyzeButton = document.querySelector("#analyze");
const canvas = document.querySelector("#canvas");
const preview = document.querySelector("#capture-preview");
const emptyState = document.querySelector("#empty-state");
const statusText = document.querySelector("#status");
const resultBox = document.querySelector("#result");
const summaryText = document.querySelector("#summary");
const fullResult = document.querySelector("#full-result");
const speech = document.querySelector("#speech");
const question = document.querySelector("#question");

let cameraStream = null;
let videoObjectUrl = null;
let audioObjectUrl = null;
let captureObjectUrl = null;
let isAnalyzing = false;

function setStatus(message, isError = false) {
  statusText.textContent = message;
  statusText.classList.toggle("error", isError);
}

function stopCamera() {
  if (cameraStream) cameraStream.getTracks().forEach((track) => track.stop());
  cameraStream = null;
  cameraStop.disabled = true;
}

function clearVideoUrl() {
  if (videoObjectUrl) URL.revokeObjectURL(videoObjectUrl);
  videoObjectUrl = null;
}

function showVideo() {
  video.style.display = "block";
  emptyState.hidden = true;
}

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (!file) return;
  stopCamera();
  clearVideoUrl();
  videoObjectUrl = URL.createObjectURL(file);
  video.srcObject = null;
  video.src = videoObjectUrl;
  video.controls = true;
  showVideo();
  setStatus("동영상을 재생하고 분석할 장면에서 멈춰 주세요.");
});

cameraStart.addEventListener("click", async () => {
  try {
    stopCamera();
    clearVideoUrl();
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    video.removeAttribute("src");
    video.srcObject = cameraStream;
    video.controls = false;
    await video.play();
    showVideo();
    cameraStop.disabled = false;
    setStatus("카메라가 시작되었습니다. 원하는 장면에서 분석 버튼을 누르세요.");
  } catch (error) {
    setStatus(`카메라를 시작할 수 없습니다: ${error.message}`, true);
  }
});

cameraStop.addEventListener("click", () => {
  stopCamera();
  video.srcObject = null;
  analyzeButton.disabled = true;
  setStatus("카메라를 중지했습니다.");
});

video.addEventListener("loadeddata", () => { analyzeButton.disabled = false; });

function canvasToBlob() {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("프레임을 JPEG로 만들지 못했습니다.")), "image/jpeg", 0.8);
  });
}

async function apiError(response) {
  try {
    const body = await response.json();
    return body.detail || `요청 실패 (${response.status})`;
  } catch {
    return `요청 실패 (${response.status})`;
  }
}

analyzeButton.addEventListener("click", async () => {
  if (isAnalyzing || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return;
  isAnalyzing = true;
  analyzeButton.disabled = true;
  resultBox.hidden = true;
  setStatus("현재 장면을 캡처하고 분석하고 있습니다.");

  try {
    const scale = Math.min(1, 1280 / video.videoWidth);
    canvas.width = Math.max(1, Math.round(video.videoWidth * scale));
    canvas.height = Math.max(1, Math.round(video.videoHeight * scale));
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    const image = await canvasToBlob();

    if (captureObjectUrl) URL.revokeObjectURL(captureObjectUrl);
    captureObjectUrl = URL.createObjectURL(image);
    preview.src = captureObjectUrl;
    preview.hidden = false;

    const form = new FormData();
    form.append("image", image, "video-frame.jpg");
    form.append("question", question.value.trim());
    const analysisResponse = await fetch("/api/media/image-analysis", { method: "POST", body: form });
    if (!analysisResponse.ok) throw new Error(await apiError(analysisResponse));
    const analysis = await analysisResponse.json();

    setStatus("분석을 완료했습니다. 안내 음성을 생성하고 있습니다.");
    const ttsResponse = await fetch("/api/media/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: analysis.summary,
        voice: "coral",
        instructions: "한국어로 짧고 명확하게 안내하세요."
      })
    });
    if (!ttsResponse.ok) throw new Error(await apiError(ttsResponse));
    const audio = await ttsResponse.blob();

    speech.pause();
    if (audioObjectUrl) URL.revokeObjectURL(audioObjectUrl);
    audioObjectUrl = URL.createObjectURL(audio);
    speech.src = audioObjectUrl;
    summaryText.textContent = analysis.summary;
    fullResult.textContent = JSON.stringify(analysis, null, 2);
    resultBox.hidden = false;
    setStatus("분석과 음성 안내가 완료되었습니다.");
    speech.play().catch(() => setStatus("분석 완료. 재생 버튼을 눌러 안내 음성을 들어 주세요."));
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    isAnalyzing = false;
    analyzeButton.disabled = video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA;
  }
});

window.addEventListener("beforeunload", () => {
  stopCamera();
  clearVideoUrl();
  if (audioObjectUrl) URL.revokeObjectURL(audioObjectUrl);
  if (captureObjectUrl) URL.revokeObjectURL(captureObjectUrl);
});
