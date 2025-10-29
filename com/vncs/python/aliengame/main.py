
from pathlib import Path
from dotenv import load_dotenv
import os
from datetime import datetime
load_dotenv()


       

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

    print("Witaj w grze Alien Game!")

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






