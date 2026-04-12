# Używamy lekkiej, oficjalnej wersji Pythona
FROM python:3.11-slim

# Instalujemy ffmpeg (wymagane przez yt-dlp do konwersji mp3)
# Używamy flag zmniejszających rozmiar obrazu
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Ustawiamy katalog roboczy wewnątrz kontenera
WORKDIR /app

# Kopiujemy plik z wymaganiami i instalujemy je (robimy to na początku, 
# aby Docker mógł "zakeszować" ten krok i nie pobierał bibliotek przy każdej zmianie w kodzie)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiujemy nasz główny kod
COPY main.py .

# Tworzymy folder na pobrane pliki (choć skrypt też to robi)
RUN mkdir -p downloads

# Informujemy, że kontener będzie nasłuchiwał na porcie 8000
EXPOSE 7583

# Komenda startowa. 
# WAŻNE: "--host 0.0.0.0" jest kluczowe w Dockerze, aby wystawić serwer na zewnątrz kontenera!
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7583"]