from http import client
import json
from pyexpat import model
import sys as system
from urllib import response;
from pathlib import Path
import openai
from dotenv import load_dotenv
import os
from datetime import datetime
load_dotenv()

# Ustaw swój klucz API
openai.api_key = os.getenv("OPENAI_API_KEY")  # lub wpisz bezpośrednio

# Wybierz model, np. "gpt-3.5-turbo", "gpt-4", "gpt-5-mini"
MODEL = "gpt-3.5-turbo"

ASSISTANT_ID = "asst_nZcsP8WSRpDG4OGdBXcCwsLA"   # ID Twojego asystenta z panelu OpenAI
PROMPT_ID = "pmpt_68fa28834d4881938d669d15a9ef6e4003bf844d71ad8a0a"         # ID Twojego promptu z panelu OpenAI

RolaKwalifikator2 = """
Rola:
Jesteś agentem klasyfikującym tekst. Twoim zadaniem jest przypisać każdy otrzymany tekst do jednej z predefiniowanych obiekcji.

Zasady:
- Po "Start kwalifikacji": odpisz dokładnie "Gotowy".
- Po "Interpretacja Start": nie odpowiadaj, oczekuj tekstu do klasyfikacji.
- Po "Stop kwalifikacji": zakończ pracę jako agent klasyfikujący i wróć do normalnego trybu.

Format odpowiedzi dla każdego tekstu:
Obiekcja: [nazwa obiekcji]
Plik: [przypisany plik]
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

Interpretacja Start.
"""


RolaKwalifikator = """Rola:
Pełnisz rolę agenta klasyfikującego tekst. Twoim zadaniem jest przypisać każdy otrzymany tekst do jednej z predefiniowanych obiekcji, z którą najbardziej się pokrywa.

Zasady działania:

- Gdy pojawi się komunikat „Interpretacja Start”, nie odpowiadaj — po prostu oczekuj na tekst do klasyfikacji.
- Gdy pojawi się tekst do kwalifikacji kwalifikuj go i zwróć wynik.
- Gdy pojawi się tekst "Start kwalifikacji". Rozpocznij swoją pracę zwracając informacje o swojej gotowości dokładnie tekstem "Gotowy"
- Gdy pojawi się tekst "Stop kwalifikacji". Zakończ swoją pracę jako agent klasyfikujący i wróć do swojego normalnego działania

Dla każdego przesłanego tekstu dokonaj interpretacji i zwróć wynik w dokładnym formacie:

Obiekcja: [nazwa obiekcji]
Plik: [plik przydzielony do obiekcji]
Dodatkowo: [jeżeli w opisie obiekcji jest zawarta informacja o tym co ma się zawierać w tym polu to zastosuj się do tych wskazań, jeżeli nie ma to nie zwracaj nic w tym polu]

Zestaw obiekcji:

OBIEKCJA: Brak zainteresowania
PLIK: brak_zainteresowania.wav
OPIS: Klient nie jest zainteresowany rozmową, produktem lub ofertą.
PRZYKŁADY:
- „Nie jestem zainteresowany.”
- „Dziękuję, ale nie potrzebuję tego.”
- „Proszę nie dzwonić więcej.”

---

OBIEKCJA: Brak czasu
PLIK: brak_czasu.wav
OPIS: Klient twierdzi, że nie ma czasu na rozmowę lub decyzję.
PRZYKŁADY:
- „Nie mam teraz czasu, oddzwonię później.”
- „Zajmuję się czymś innym, proszę zadzwonić jutro.”
- „Nie mogę teraz rozmawiać.”

---

OBIEKCJA: Nie ufam
PLIK: nieufam.wav
OPIS: Klient wyraża brak zaufania do procesu sprzedaży lub handlowca.
PRZYKŁADY:
- „Nie wierzę w takie oferty.”
- „Już raz się naciąłem, nie dziękuję.”
- „Nie ufam sprzedawcom przez telefon.”

---

OBIEKCJA: Za drogo
PLIK: zadrogo.wav
OPIS: Klient uważa, że cena jest zbyt wysoka lub nieadekwatna do wartości.
PRZYKŁADY:
- „Za drogie, nie stać mnie.”
- „U konkurencji jest taniej.”
- „To nie jest warte takiej ceny.”

---

OBIEKCJA: Nierozpoznany
PLIK: nierozpoznany.wav
OPIS: Wypowiedź klienta nie pasuje jednoznacznie do żadnej kategorii obiekcji. Lub jest jednoznacznie nie na temat
PRZYKŁADY:
- „Ładna pogoda.”
- „Nie wiem, muszę się zastanowić.”
- „Trudno mi powiedzieć.”
- „To zależy, muszę porozmawiać z kimś innym.”

---

OBIEKCJA: Dane osobowe
PLIK: dane_osobowe.wav
OPIS: Klient przedstawia się podając imię lub nazwisko
DODATKOWO: W tym polu umieść tylko rozpoznane imię i nazwisko
PRZYKŁADY:
- „Arkadiusz Burdon.”
- „Imię to będzie Zenon.”
- „Moje nazwisko to Dzierżyński.”
- „No dobrze. To będzie Feliks Amatorski”

---

OBIEKCJA: Dane adresowe
PLIK: dane_adresowe.wav
OPIS: Klient podał dane adresowe np. ulicę, miejscowość, kod pocztowy
PRZYKŁADY:
- „Jestem z Legionowa”
- „Mieszka w Warszawie na ulicy Górnośląskiej”


Interpretacja Start.
"""

RolaChatbot = """
Rola:
Jesteś asystentem AI zaprojektowanym do prowadzenia rozmów z użytkownikami. Twoim zadaniem jest odpowiadanie na pytania, udzielanie informacji i pomaganie w rozwiązywaniu problemów w sposób uprzejmy i pomocny.
Zasady działania:
- Odpowiadaj na pytania użytkowników w sposób jasny i zwięzły.
- Używaj uprzejmego i przyjaznego tonu.
- Jeśli nie znasz odpowiedzi na pytanie, przyznaj się do tego i zasugeruj, gdzie użytkownik może znaleźć więcej informacji.
 


"""

instrukcje= RolaKwalifikator

def use_chatcompletion():
    """Użycie klasycznego ChatCompletion dla starszych modeli"""
    conversation = []
    print("Terminalowy czat (ChatCompletion) – wpisz 'exit' aby zakończyć")
    
    while True:
        user_input = input("Ty: ")
        if user_input.lower() == "exit":
            break
        
        conversation.append({"role": "user", "content": user_input})
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=conversation,
            temperature=0.7
        )
        reply = response.choices[0].message['content']
        print("GPT:", reply)
        conversation.append({"role": "assistant", "content": reply})

def use_responses():
    """Użycie nowego client.responses.create dla nowszych modeli"""
    from openai import OpenAI
    client = OpenAI(api_key=openai.api_key)
    
    print("Terminalowy czat (Responses API) – wpisz 'exit' aby zakończyć")
    conversation = []
    
    while True:
        user_input = input("Ty: ")
        if user_input.lower() == "exit":
            break
        
        conversation.append({"role": "user", "content": user_input})
        response = client.responses.create(
            model=MODEL,
            input=conversation
        )
        # Prosty tekst odpowiedzi
        reply = response.output_text
        print("GPT:", reply)
        conversation.append({"role": "assistant", "content": reply})
        
def use_chat_streaming():
    conversation = []
    print("Terminalowy czat (Streaming) – wpisz 'exit' aby zakończyć")
    
    while True:
        user_input = input("Ty: ")
        if user_input.lower() == "exit":
            break
        
        conversation.append({"role": "user", "content": user_input})
        
        # Streamowanie odpowiedzi
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=conversation,
            temperature=0.7,
            stream=True  # <-- tu włączamy streaming
        )
        
        print("GPT: ", end="", flush=True)
        reply_text = ""
        
        for chunk in response:
            delta = chunk['choices'][0]['delta']
            if "content" in delta:
                print(delta['content'], end="", flush=True)
                reply_text += delta['content']
        
        print()  # nowa linia po odpowiedzi
        conversation.append({"role": "assistant", "content": reply_text})
        

        
def use_chat_responses_streaming():
    conversation = []
    print(f"Terminalowy czat model: {MODEL} (Responses API Streaming) – wpisz 'exit' aby zakończyć")
    user_input = input("To zostanie pominiete: ")
    
    from openai import OpenAI
    client = OpenAI(api_key=openai.api_key)
    
    models = client.models.list()
    for m in models.data:
        print(m.id)
    
    firstTime = True
    
    while True:
        
        if firstTime:
            firstTime = False
            user_input = instrukcje
        else:
            user_input = input("Ty: ")
            print("user_input:", user_input)
            if user_input.lower() == "exit":
                break
        
        conversation.append({"role": "user", "content": user_input})
        reply_text = ""
        
        
        # Streamowanie odpowiedzi

        timeout_start = datetime.now()
        with client.responses.stream(
            model=MODEL,
            input=conversation
        ) as stream:
            print("GPT: ", end="", flush=True)
            for event in stream:  # teraz działa poprawnie
                # event może mieć różne typy, interesuje nas delta tekstu
                if event.type == "response.output_text.delta":
                    print(event.delta, end="", flush=True)
                    reply_text += event.delta
    
        
        print(f"\nresponse time: {datetime.now() - timeout_start}")  # nowa linia po odpowiedzi
        conversation.append({"role": "assistant", "content": reply_text})
        

def chat_with_prompt_responses():
    print(openai.__version__)
    print("💬 Terminalowy czat z prompt OpenAI (Responses API)")
    print("Wpisz 'exit', aby zakończyć.\n")
    user_input = input("Czy chcesz zacząć? (tak/nie): ")
    from openai import OpenAI
    client = OpenAI(api_key=openai.api_key)
    conversation = []  # do zachowania historii w tej sesji

    while True:
        user_input = input("Ty: ")
        if user_input.lower() == "exit":
            print("👋 Zakończono czat.")
            break

        conversation.append({"role": "user", "content": user_input})

        print("Asystent: ", end="", flush=True)
        reply_text = ""
        start = datetime.now()

        # --- Streaming nowym Responses API ---
        with client.responses.stream(
            model=MODEL,
            prompt={"id": PROMPT_ID},   # prompt = nowy odpowiednik asystenta
            input=[{"role": "user", "content": user_input}],
        ) as stream:
            for event in stream:
                if event.type == "response.output_text.delta":
                    print(event.delta, end="", flush=True)
                    reply_text += event.delta
            stream.until_done()

        print(f"\n⏱ Czas odpowiedzi: {datetime.now() - start}\n")

        conversation.append({"role": "user", "content": user_input})
        conversation.append({"role": "assistant", "content": reply_text})

       

def main():
    # Diagnostic startup info (nie ujawnia sekretów) ---------------------
    import sys
    import os
    import site

    print("--- Startup diagnostic ---")
    try:
        print("executable:", sys.executable)
        print("prefix:", sys.prefix)
        print("base_prefix:", getattr(sys, "base_prefix", None))
        print("VIRTUAL_ENV:", os.environ.get("VIRTUAL_ENV"))
        in_venv = sys.prefix != getattr(sys, "base_prefix", None)
        print("in_venv:", in_venv)
        # site-packages (jeśli dostępne)
        try:
            sp = site.getsitepackages()
        except Exception:
            sp = []
        print("site.getsitepackages():", sp)
        # pokaż pierwsze wpisy sys.path, nie ujawniając wrażliwych danych
        print("sys.path (first 6):")
        for p in sys.path[:6]:
            print("  -", p)
    except Exception as _e:
        print("Startup diagnostic error:", _e)
    print("--- End diagnostic ---\n")

    # Jeśli model jest starszy – używamy ChatCompletion, jeśli nowszy – Responses
    #if MODEL.startswith("gpt-3") or MODEL.startswith("gpt-4"):
    #    chat_with_prompt_responses()
    #else:
    #    #use_responses()
    chat_with_prompt_responses()

if __name__ == "__main__":
    main()

# def main():
#     print("Witaj w projekcie TestOpenAI!")
#     print(system.executable)
#     print(system.version)
#     
#     now = datetime.now()
#     print("Aktualny czas:", now.strftime("%Y-%m-%d %H:%M:%S"))
#     
#     client = OpenAI(
#         api_key=os.getenv("OPENAI_API_KEY")
#     )
#
#     response = client.responses.create(
#         model="gpt-5-mini",
#         input="Powtórz tekst: Witaj świecie"      
#     )
#
#     print(response.output_text)
#     now2 = datetime.now()
#     diff_seconds = (now2 - now).total_seconds()
#     print(f"Czas wykonania: {diff_seconds:.3f}")






