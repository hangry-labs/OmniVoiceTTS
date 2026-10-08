<p align="center">
  <a href="https://hangry-labs.github.io/OmniVoiceTTS/examples/?lang=nb">
    <img src="assets/omnivoice_logo_horizontal.webp" alt="Hangry Labs OmniVoiceTTS-logo" width="900">
  </a>
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <strong>Norsk bokmål</strong> ·
  <a href="README.pl.md">Polski</a> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.zh.md">简体中文</a> ·
  <a href="README.es.md">Español</a>
</p>

# Hangry Labs OmniVoiceTTS

Docker-klar, svært flerspråklig tekst-til-tale med lokalt nettlesergrensesnitt, HTTP-API, stemmedesign og stemmekloning.

Denne Hangry Labs-versjonen er laget for enkel lokal inferens. Start én container, åpne grensesnittet eller kall API-et, og lag tale uten å sette opp Python, modeller, ASR eller lydverktøy manuelt.

## Dette får du

- Lokalt nettlesergrensesnitt for generering, strømming, avspilling og nedlasting
- OpenAI-kompatibelt endepunkt på `/v1/audio/speech` og et komplett innebygd API
- Automatisk stemme, stemmedesign, direkte stemmekloning og lagrede stemmeprofiler
- Standard SSML og SSML-H for kontrollert tale og dialog med flere karakterer
- Støtte for mer enn 600 språk fra OmniVoice
- WAV, MP3, FLAC og OGG
- Valgfri MCP-integrasjon for lokale KI-agenter
- Komplett Docker-bilde som kan brukes uten nett etter nedlasting

> [!IMPORTANT]
> Kildekoden er Apache-2.0, men den forhåndstrente OmniVoice-modellen beskrives av oppstrømsprosjektet som `CC-BY-NC` og er ikke lisensiert for kommersiell bruk. Les [tredjepartsmerknadene](THIRD_PARTY_NOTICES.md) før bruk eller videre distribusjon.

## Hurtigstart

Kjør det komplette bildet med en NVIDIA-GPU:

```bash
docker run --name omnivoicetts --restart unless-stopped -p 7861:7861 --gpus all -e CUDA_VISIBLE_DEVICES=0 -v omnivoicetts_data:/app/persistent hangrylabs/omnivoicetts:latest
```

Kommandoen står på én linje og kan limes direkte inn i Bash, PowerShell eller Windows Ledetekst. Docker oppretter det navngitte volumet automatisk.

Åpne deretter:

- Nettlesergrensesnitt: [http://localhost:7861](http://localhost:7861)
- API-dokumentasjon: [http://localhost:7861/tts/docs](http://localhost:7861/tts/docs)
- [Eksempler på språk og stemmer](https://hangry-labs.github.io/OmniVoiceTTS/examples/?lang=nb)

Volumet `omnivoicetts_data` beholder modeller, innstillinger og lagrede stemmer når containeren erstattes eller bildet oppdateres. Det komplette bildet inkluderer de nødvendige modellressursene og kan brukes uten nett etter nedlasting.

Publiserte GitHub-utgivelser og tilhørende Git-tagger er uforanderlige. Versjonerte Docker-tagger er også uforanderlige, mens `latest` og `latest_tiny` med vilje peker på det nyeste øyeblikksbildet.

## Mer informasjon

Les den [komplette norske produkt- og installasjonsveiledningen](https://hangrylabs.app/nb/software/omnivoicetts). Den fullstendige tekniske referansen vedlikeholdes i den [engelske README-filen](README.md). Feil og forslag kan rapporteres i [GitHub Issues](https://github.com/Hangry-Labs/OmniVoiceTTS/issues).
