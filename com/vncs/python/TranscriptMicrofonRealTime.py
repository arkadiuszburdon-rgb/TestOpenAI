import asyncio, json, sounddevice as sd, websockets, os, time ,base64 ,wave
from dotenv import load_dotenv
import numpy as np

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4o-realtime-preview-2024-12-17"
SAMPLE_RATE = 16000

LOG_EVENTS_TYPES = [
    "session.created",
    "session.capabilities",
    "input_audio_buffer.appended",
    "input_audio_buffer.committed",
    "response.created",
    "response.created",
    "response.output_text.delta",
    "response.output_text.append",
    "response.output_text.done",
    "response.completed",
    "error"
]


def wav_writer(filename="mic_test.wav", sample_rate=16000):
    wf = wave.open(filename, 'wb')
    wf.setnchannels(1)        # mono
    wf.setsampwidth(2)        # 16-bit PCM = 2 bytes
    wf.setframerate(sample_rate)
    return wf

def is_voice(pcm, threshold=500):
    # konwersja bajtów do tablicy int16
    audio = np.frombuffer(pcm, dtype=np.int16)
    # energia sygnału
    energy = np.mean(np.abs(audio))
    print(f"Energy: {energy}")
    return energy > threshold

async def run():
    print("🎤 Start — mów")
    
    wav = wav_writer()

    ws = await websockets.connect(
        f"wss://api.openai.com/v1/realtime?model={MODEL}",
        extra_headers={
            "Authorization": f"Bearer {API_KEY}",
            "OpenAI-Beta": "realtime=v1"  # ✅ TO JEST KLUCZ
        },
        max_size=None
    )

    print("✅ Połączono z Realtime API")
    
    
    

    # ✅ wymagane przez Twoją wersję API
    await ws.send(json.dumps({
        "type": "session.update",
        "session": {
            "modalities": ["audio", "text"],      # streaming audio IN
            "instructions": "Transcribe speech to Polish text. Output ONLY the transcript.",
            "input_audio_format": "pcm16",  # najważniejsze!
            "output_audio_format": "pcm16",
            "turn_detection": None         # bez auto-VAD (na razie)
        }
    }))
    
    

    CHUNK = 2048
    pending = False
    buffer_ms = 0

    async def mic():
        nonlocal pending, buffer_ms
        talking = False
        silence_frames = 0
        has_voice_data = False  # ✅ nowa flaga: czy mikrofon dał już głos

        with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as stream:
            while True:
                data, _ = stream.read(CHUNK)
                pcm = bytes(data)

                # zapis WAV
                wav.writeframes(pcm)

                # VAD: czy jest mowa?
                voice = is_voice(pcm)

                if voice:
                    talking = True
                    silence_frames = 0
                    has_voice_data = True  # ✅ pierwszy głos się pojawił
                else:
                    if talking:
                        silence_frames += 1

                # wysyłamy audio tylko jeśli już był głos
                if has_voice_data and (talking or silence_frames < 5):
                    # wysyłamy audio chunk
                    await ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(pcm).decode("utf-8")
                    }))
                    buffer_ms += (len(pcm) / 2 / SAMPLE_RATE) * 1000

                # ⛔ nie commituj, jeśli NIE było mowy
                if not has_voice_data:
                    await asyncio.sleep(0.001)
                    continue

                # ✅ commit TYLKO gdy:
                # - mówiliśmy
                # - jest kilka ramek ciszy
                # - mamy >120 ms audio
                # - model nie jest zajęty odpowiedzią
                if talking and silence_frames >= 5 and buffer_ms > 120 and not pending:
                    print("\n--- Committing buffer ---\n")
                    await ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                    await ws.send(json.dumps({
                        "type": "response.create",
                        "response": {
                            "modalities": ["text"]
                        }
                    }))
                    pending = True
                    buffer_ms = 0.0
                    talking = False
                    has_voice_data = False  # ✅ poczekamy na kolejne zdanie

                await asyncio.sleep(0.001)



    async def rx():
        nonlocal pending
        async for msg in ws:
            evt = json.loads(msg)
            t = evt.get("type")
            
            
            if "text" in evt:
                print(f"{t} - TEXT EVENT RAW:", evt)


            # ===========================
            # LOG WSZYSTKIE EVENTY
            # ===========================
            # UWAGA — NIE PRINTUJ TEKSTU TUTAJ
            print(f"[EVENT] {t}")

            # ===========================
            # STREAMOWANIE TEKSTU
            # ===========================
            if t == "response.text.delta":
                if "text" in evt:
                    print(evt["text"], end="", flush=True)
                continue

            # główne miejsce odbioru tekstu
            elif t == "response.text.done":
                print(evt.get("text", ""))
                print("\n---\n")
                pending = False
                continue


    await asyncio.gather(mic(), rx())

asyncio.run(run())
