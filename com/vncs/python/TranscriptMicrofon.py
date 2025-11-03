import sounddevice as sd
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
import threading, wave, time, os
from io import BytesIO
from datetime import datetime

# =======================================
# Tenskrypcja za pomocą modelu Wisper. Mikrofon zbiera dzwęk do pliku WAV na dysku.
# Odczytujemy tylko nowe ramki z pliku WAV i dopisujemy je do bufora w RAM.
# Co 0.4 sekundy wysyłamy cały bufor audio do modelu Whisper, aby uzyskać pełną transkrypcję.
# =======================================   
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SAMPLE_RATE = 16000
BLOCK_SIZE = 2048
WAV_FILE = "mic_buffer.wav"
TRANSCRIPT_FILE = "live_transcript.txt"

processed_frames = 0
audio_buffer = bytearray()   # ✅ RAM audio buffer


# =======================================
# Microphone thread — writes a single growing WAV
# =======================================
def mic_thread():
    print("🎤 Recorder thread started")

    wf = wave.open(WAV_FILE, "wb")
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SAMPLE_RATE)

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        blocksize=BLOCK_SIZE,
        dtype="float32"
    )
    stream.start()

    try:
        while True:
            data, _ = stream.read(BLOCK_SIZE)
            pcm = (data * 32767).astype(np.int16).tobytes()
            wf.writeframes(pcm)
            wf._file.flush()
    except KeyboardInterrupt:
        stream.stop()
        wf.close()
        print("🛑 Recorder stopped")


# =======================================
# Convert buffer to WAV in memory
# =======================================
def make_wav_from_buffer(buffer_bytes):
    buf = BytesIO()
    with wave.open(buf, "wb") as w2:
        w2.setnchannels(1)
        w2.setsampwidth(2)
        w2.setframerate(SAMPLE_RATE)
        w2.writeframes(buffer_bytes)
    buf.seek(0)
    return buf


# =======================================
# STT thread — accumulate audio in RAM and send full buffer
# =======================================
def stt_thread():
    global processed_frames, audio_buffer

    print("🧠 Transcriber thread started")
    open(TRANSCRIPT_FILE, "w", encoding="utf-8").close()
    full_text = ""

    try:
        while True:
            time.sleep(0.4)

            file_size = os.path.getsize(WAV_FILE)
            total_frames = file_size // 2

            if total_frames <= processed_frames:
                continue

            start = processed_frames
            end = total_frames
            if (end - start) < int(SAMPLE_RATE * 0.1):
                continue

            processed_frames = end

            # ✅ read only the NEW frames
            with wave.open(WAV_FILE, "rb") as wf:
                wf.setpos(start)
                new_chunk = wf.readframes(end - start)

            # ✅ append to RAM buffer
            audio_buffer.extend(new_chunk)

            # ✅ build WAV from full memory buffer
            wav_mem = make_wav_from_buffer(audio_buffer)

            # ✅ send full accumulated audio, not only chunk
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=("full_buffer.wav", wav_mem, "audio/wav"),
                response_format="text",
                language="pl"
            )

            text = response.strip()
            full_text = text  # ✅ always full transcript replaced
            print("👉", text)

            ts = datetime.now().strftime("%H:%M:%S")
            with open(TRANSCRIPT_FILE, "w", encoding="utf-8") as f:
                f.write(f"[{ts}] {text}\n")

    except KeyboardInterrupt:
        print("\n✅ Final transcript:\n", full_text)


# =======================================
# Main
# =======================================
def main():
    t1 = threading.Thread(target=mic_thread, daemon=True)
    t2 = threading.Thread(target=stt_thread, daemon=True)

    t1.start()
    t2.start()

    t1.join()
    t2.join()


if __name__ == "__main__":
    print("🚀 Start — mów. CTRL+C kończy.")
    main()
