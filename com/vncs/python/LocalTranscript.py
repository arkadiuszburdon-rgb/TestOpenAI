import os, numpy as np, sounddevice as sd, time
from faster_whisper import WhisperModel

os.environ["CT2_FORCE_CPU"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

MODEL_PATH = r"D:\Praca\ProjektyPython\TestOpenAI\models\whisper-small-pl"
model = WhisperModel(MODEL_PATH, device="cpu", compute_type="int8")

MIC_DEVICE = 3  # ← tu wstaw numer mikrofonu

SAMPLE_RATE = 16000
buffer = np.array([], dtype=np.float32)

def callback(indata, frames, t, status):
    global buffer
    buffer = np.concatenate((buffer, indata[:,0]))

stream = sd.InputStream(
    samplerate=SAMPLE_RATE,
    channels=1,
    device=MIC_DEVICE,
    callback=callback
)
stream.start()

print("🎤 Mów — co 2s spróbujemy rozpoznać tekst")

while True:
    time.sleep(2)
    if len(buffer) < SAMPLE_RATE * 0.3:
        continue
    data = buffer.copy()
    buffer = np.array([], dtype=np.float32)
    segs, _ = model.transcribe(data, language="pl")
    for s in segs:
        txt = s.text.strip()
        if txt:
            print("🗣️", txt)
