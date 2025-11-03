import asyncio, json, sounddevice as sd, websockets, os, time ,base64 ,wave
from dotenv import load_dotenv
from openai import OpenAI
import numpy as np

"""
Projekt: Klasyfikator obiekcji w czasie rzeczywistym podczas rozmowy telefonicznej.
Opis: Ten skrypt nasłuchuje mikrofonu, wykrywa mowę i wysyła audio do OpenAI Realtime API.
Model analizuje wypowiedzi klientów i klasyfikuje je według predefiniowanych obiekcji sprzedażowych.
Model: gpt-realtime-2025-08-28
"""


load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
#MODEL = "gpt-4o-realtime-preview-2024-12-17"
MODEL = "gpt-realtime-2025-08-28"
SAMPLE_RATE = 16000

RolaKwalifikator2 = """
Rola:

Jesteś agentem klasyfikującym tekst.  Twoim zadaniem jest przypisać każdy otrzymany tekst do jednej z predefiniowanych obiekcji.
Kwalifikowane teksty pochodzą od klientów podczas rozmów telefonicznych dotyczących sprzedaży produktów lub usług.
Kwalifikujesz wypowiedzi klientów, które mogą zawierać obiekcje lub dane osobowe.
Kwalifikowane teksty są krótkie, zwykle jedno- lub dwuzdaniowe.
Kwalifikowane teksty są wyłącznie w języku polskim.
Zoptymalizuj swoje działanie uwzględniając fakt, że teksty są wyłącznie w języku polskim.

Zasady:
- 
- Po "Start kwalifikacji": odpisz dokładnie "Gotowy".
- Po "Start kwalifikacji": nie odpowiadaj, oczekuj tekstu do klasyfikacji.
- Po "Stop kwalifikacji": zakończ pracę jako agent klasyfikujący i wróć do normalnego trybu.
- Bezwzględnie trzymaj się zasad.

Format odpowiedzi dla każdego tekstu:
Obiekcja: [nazwa obiekcji]
Plik: [przypisany plik]
Klasyfikowany tekst: [oryginalny tekst]
Dodatkowo: wypełnij tylko jeśli opis obiekcji wymaga tej informacji; w przeciwnym razie pozostaw puste.

Zestaw obiekcji:

OBIEKCJA: Brak zainteresowania
PLIK: brak_zainteresowania.wav
OPIS: Klient nie jest zainteresowany rozmową, produktem lub ofertą.
PRZYKŁADY:
- "Nie jestem zainteresowany."
- "Dziękuję, ale nie potrzebuję tego."
- "Proszę nie dzwonić więcej."

OBIEKCJA: Brak czasu
PLIK: brak_czasu.wav
OPIS: Klient twierdzi, że nie ma czasu na rozmowę lub decyzję.
PRZYKŁADY:
- "Nie mam teraz czasu, oddzwonię później."
- "Zajmuję się czymś innym, proszę zadzwonić jutro."
- "Nie mogę teraz rozmawiać."

OBIEKCJA: Nie ufam
PLIK: nieufam.wav
OPIS: Klient wyraża brak zaufania do procesu sprzedaży lub handlowca.
PRZYKŁADY:
- "Nie wierzę w takie oferty."
- "Już raz się naciąłem, nie dziękuję."
- "Nie ufam sprzedawcom przez telefon."

OBIEKCJA: Za drogo
PLIK: zadrogo.wav
OPIS: Klient uważa, że cena jest zbyt wysoka lub nieadekwatna do wartości.
PRZYKŁADY:
- "Za drogie, nie stać mnie."
- "U konkurencji jest taniej."
- "To nie jest warte takiej ceny."

OBIEKCJA: Nierozpoznany
PLIK: nierozpoznany.wav
OPIS: Wypowiedź klienta nie pasuje jednoznacznie do żadnej kategorii obiekcji lub jest nie na temat.
PRZYKŁADY:
- "Ładna pogoda."
- "Nie wiem, muszę się zastanowić."
- "Trudno mi powiedzieć."
- "To zależy, muszę porozmawiać z kimś innym."

OBIEKCJA: Dane osobowe
PLIK: dane_osobowe.wav
OPIS: Klient przedstawia się podając imię lub nazwisko.
DODATKOWO: W tym polu umieść tylko rozpoznane imię i nazwisko.
PRZYKŁADY:
- "Arkadiusz Burdon."
- "Imię to będzie Zenon."
- "Moje nazwisko to Dzierżyński."
- "No dobrze. To będzie Feliks Amatorski"

OBIEKCJA: Dane adresowe
PLIK: dane_adresowe.wav
OPIS: Klient podał dane adresowe np. ulicę, miejscowość, kod pocztowy.
PRZYKŁADY:
- "Jestem z Legionowa."
- "Mieszka w Warszawie na ulicy Górnośląskiej."
- "To będzie Kraków."

Start kwalifikacji
"""


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
    #print(f"Energy: {energy}")
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
            "instructions": RolaKwalifikator2,
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
            
            
            #if "text" in evt:
            #    print(f"{t} - TEXT EVENT RAW:", evt)


            # ===========================
            # LOG WSZYSTKIE EVENTY
            # ===========================
            # UWAGA — NIE PRINTUJ TEKSTU TUTAJ
            #print(f"[EVENT] {t}")

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
                await ws.send(json.dumps({"type": "session.reset"}))
                continue


    await asyncio.gather(mic(), rx())
 
from openai import OpenAI

client = OpenAI(api_key=API_KEY)

models = client.models.list()

for m in models.data:
    print(m.id)


asyncio.run(run())
