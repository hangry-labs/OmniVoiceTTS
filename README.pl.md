<p align="center">
  <a href="https://hangry-labs.github.io/OmniVoiceTTS/examples/?lang=pl">
    <img src="assets/omnivoice_logo_horizontal.webp" alt="Logo Hangry Labs OmniVoiceTTS" width="900">
  </a>
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.nb.md">Norsk bokmål</a> ·
  <strong>Polski</strong> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.zh.md">简体中文</a> ·
  <a href="README.es.md">Español</a>
</p>

# Hangry Labs OmniVoiceTTS

Gotowy do użycia w Dockerze, bardzo wielojęzyczny system zamiany tekstu na mowę z lokalnym interfejsem przeglądarkowym, API HTTP, projektowaniem głosu i klonowaniem głosu.

Ta wersja Hangry Labs została przygotowana z myślą o prostej lokalnej inferencji. Uruchom jeden kontener, otwórz interfejs albo wywołaj API i generuj mowę bez ręcznej konfiguracji Pythona, modeli, ASR czy narzędzi audio.

## Co oferuje projekt

- Lokalny interfejs do generowania, strumieniowania, odtwarzania i pobierania audio
- Endpoint `/v1/audio/speech` zgodny z OpenAI oraz kompletne wbudowane API
- Głos automatyczny, projektowanie głosu, bezpośrednie klonowanie i zapisane profile głosowe
- Standardowy SSML i SSML-H do kontrolowanej mowy oraz dialogów wielu postaci
- Obsługę ponad 600 języków zapewnianą przez OmniVoice
- Format WAV, MP3, FLAC i OGG
- Opcjonalną integrację MCP dla lokalnych agentów AI
- Pełny obraz Docker działający offline po pobraniu

> [!IMPORTANT]
> Kod źródłowy korzysta z licencji Apache-2.0, ale wstępnie wytrenowany model OmniVoice jest opisany przez projekt nadrzędny jako `CC-BY-NC` i nie jest licencjonowany do użytku komercyjnego. Przed użyciem lub redystrybucją przeczytaj [informacje o komponentach zewnętrznych](THIRD_PARTY_NOTICES.md).

## Szybki start

Uruchom pełny obraz z kartą NVIDIA:

```bash
docker run --name omnivoicetts --restart unless-stopped -p 7861:7861 --gpus all -e CUDA_VISIBLE_DEVICES=0 -v omnivoicetts_data:/app/persistent hangrylabs/omnivoicetts:latest
```

Polecenie znajduje się w jednym wierszu i można je wkleić bezpośrednio do Bash, PowerShell lub Wiersza polecenia Windows. Docker automatycznie utworzy nazwany wolumin.

Następnie otwórz:

- Interfejs: [http://localhost:7861](http://localhost:7861)
- Dokumentację API: [http://localhost:7861/tts/docs](http://localhost:7861/tts/docs)
- [Przykłady języków i głosów](https://hangry-labs.github.io/OmniVoiceTTS/examples/?lang=pl)

Wolumin `omnivoicetts_data` zachowuje modele, ustawienia i zapisane głosy po wymianie kontenera lub aktualizacji obrazu. Pełny obraz zawiera wymagane zasoby modeli i po pobraniu może działać offline.

## Więcej informacji

Przeczytaj [pełny polski opis produktu i instrukcję instalacji](https://hangrylabs.app/pl/software/omnivoicetts). Pełna dokumentacja techniczna jest utrzymywana w [angielskim pliku README](README.md). Błędy i propozycje można zgłaszać w [GitHub Issues](https://github.com/Hangry-Labs/OmniVoiceTTS/issues).
