import asyncio, json, sounddevice as sd, websockets, os, base64
from dotenv import load_dotenv
from datetime import datetime
import keyboard

#----------------------------------------------------------
# Projekt: Naturalny asystent głosowy mówiący po polsku.
# Odpowiada naturalnie i zwięźle.   
# Nie powtarza użytkownika — odpowiada sensownie.
# Detekcja mowy i zarządzanie turami przez serwer (OpenAI Realtime API).
# Ograniczona odpowiedź tylko do tekstu (bez audio zwrotnego).
# Wykorzystuje WebSocket do komunikacji w czasie rzeczywistym.
#-----------------------------------------------

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

MODEL = "gpt-4o-realtime-preview"
SAMPLE_RATE = 24000
CHUNK = 1024

 

SYSTEM_PROMPT = """
Jesteś asystentem głosowym mówiącym po polsku.
Odpowiadaj naturalnie, zwięźle i przyjaźnie.
Nie powtarzaj użytkownika — odpowiadaj sensownie.
"""




# 🔄 nadpisujemy logi przy starcie
open("events.log", "w").close()

with open("events.log", "w", encoding="utf-8") as f:
    f.write("Start logów")


def select_default_microphone():
    devices = sd.query_devices()
    default_mic_index = None

    for idx, dev in enumerate(devices):
        # Szukamy domyślnego wejścia laptopa
        if dev['max_input_channels'] > 0 and ("Microphone" in dev['name'] or "Realtek" in dev['name'] or "Internal" in dev['name']):
            default_mic_index = idx
            break

    if default_mic_index is None:
        print("⚠️ Nie znaleziono mikrofonu laptopa — używam domyślnego")
        return None
    
    print(f"✅ Wybrano mikrofon: {devices[default_mic_index]['name']}")
    sd.default.device = (None, sd.default.device[1])
    
async def run():
    
    select_default_microphone()
    #sd.default.device = (None, sd.default.device[1])

    print("🎤 Mów — nasłuchuję...")

    ws = await websockets.connect(
        f"wss://api.openai.com/v1/realtime?model={MODEL}",
        extra_headers={
            "Authorization": f"Bearer {API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    )

    await ws.send(json.dumps({
        "type": "session.update",
        "session": {
            "instructions": SYSTEM_PROMPT,
            "modalities": ["text"],
            "input_audio_format": "pcm16",
            
            # ✅ tylko stabilny VAD — bez nieobsługiwanych pól
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.6,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 200
            },

            "input_audio_transcription": {
                "model": "gpt-4o-transcribe",
                "language": "pl"
            }
        }
    }))

    audio_out_buffer = bytearray()
    mute_mic = True
    total_input_tokens = 0
    total_output_tokens = 0
    
    def audio_callback(outdata, frames, time, status):
        nonlocal audio_out_buffer
        if len(audio_out_buffer) >= frames * 2:
            chunk = audio_out_buffer[:frames * 2]
            outdata[:] = chunk
            del audio_out_buffer[:frames * 2]
        else:
            outdata[:] = b'\x00' * frames * 2

    async def mic():
        nonlocal mute_mic
        with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as stream:
            while True:
                data, _ = stream.read(CHUNK)
                pcm = bytes(data)

                if not mute_mic:
                    await ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(pcm).decode()
                    }))
                    
                await asyncio.sleep(0)

    async def rx():
        nonlocal audio_out_buffer, mute_mic, total_input_tokens, total_output_tokens

        with sd.RawOutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=audio_callback):
            async for msg in ws:

                evt = json.loads(msg)
                t = evt.get("type")

                # 📝 log do pliku (pierwsze 350 znaków)
                with open("events.log", "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] {json.dumps(evt, ensure_ascii=False)[:350]}\n")
                    
                    
                if "usage" in evt:
                    usage = evt["usage"]
                    
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)

                    total_input_tokens += input_tokens
                    total_output_tokens += output_tokens

                    print(f"📊 Tokeny: IN={input_tokens} OUT={output_tokens} | "
                        f"SUMA → IN={total_input_tokens}, OUT={total_output_tokens}, "
                        f"RAZEM={total_input_tokens + total_output_tokens}")

                if t == "input_audio_buffer.speech_started":
                    print("\n🎤 Początek wypowiedzi...")

                #if t == "conversation.item.input_audio_transcription.delta":
                    #print(evt.get("delta",""), end="", flush=True)

                if t == "conversation.item.input_audio_transcription.completed":
                    print(f"\n👤 Ty: {evt.get('transcript')}\n")
                    print("\n🎤 Zakonczenie wypowiedzi")

                if t == "response.audio_transcript.delta":
                    #print(evt.get("delta",""), end="", flush=True)
                    pass
                #gdy wylaczony dzwiek to tekst jest zwracany w tym evencie
                if t == "response.text.done":
                    print(evt.get("text",""), end="", flush=True)
                    print("\n🤖 --- Koniec odpowiedzi ---\n")
                #gdy wlaczony dzwiek to tekst jest zwracany w tym evencie
                if t == "response.audio_transcript.done":
                    print(evt.get("transcript",""), end="", flush=True)
                    print("\n🤖 --- Koniec odpowiedzi ---\n")
                    await asyncio.sleep(1)  # pozwól dokończyć odtwarzanie
                
                if t == "response.audio.delta":
                    pcm = base64.b64decode(evt["delta"])
                    audio_out_buffer.extend(pcm)
                    
                    
    # Pozwól audio-out się włączyć zanim startuje mikrofon
    # Warm-up mic mute (zapobiega pierwszemu "kliknięciu")
    mute_mic = True
    await asyncio.sleep(0.35)
    mute_mic = False
    await asyncio.gather(mic(), rx())


asyncio.run(run())
