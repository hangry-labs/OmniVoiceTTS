<p align="center">
  <a href="https://hangry-labs.github.io/OmniVoiceTTS/examples/?lang=es">
    <img src="assets/omnivoice_logo_horizontal.webp" alt="Logotipo de Hangry Labs OmniVoiceTTS" width="900">
  </a>
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.nb.md">Norsk bokmål</a> ·
  <a href="README.pl.md">Polski</a> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.zh.md">简体中文</a> ·
  <strong>Español</strong>
</p>

# Hangry Labs OmniVoiceTTS

Texto a voz masivamente multilingüe y preparado para Docker, con interfaz web local, API HTTP, diseño de voces y clonación de voz.

Esta versión de Hangry Labs está diseñada para una inferencia local sencilla. Inicia un contenedor, abre la interfaz o llama a la API y genera voz sin configurar manualmente Python, modelos, ASR ni herramientas de audio.

## Qué ofrece el proyecto

- Interfaz web local para generar, transmitir, reproducir y descargar audio
- Endpoint `/v1/audio/speech` compatible con OpenAI y una API nativa completa
- Voz automática, diseño de voces, clonación directa y perfiles de voz guardados
- SSML estándar y SSML-H para voz controlada y diálogos con varios personajes
- Más de 600 idiomas gracias a OmniVoice
- Salida WAV, MP3, FLAC y OGG
- Integración MCP opcional para agentes de IA locales
- Imagen Docker completa que funciona sin conexión después de descargarla

> [!IMPORTANT]
> El código fuente utiliza Apache-2.0, pero el proyecto original describe el modelo preentrenado de OmniVoice como `CC-BY-NC`, por lo que no está autorizado para uso comercial. Consulta los [avisos de terceros](THIRD_PARTY_NOTICES.md) antes de usarlo o redistribuirlo.

## Inicio rápido

Ejecuta la imagen completa con una GPU NVIDIA:

```bash
docker run --name omnivoicetts --restart unless-stopped -p 7861:7861 --gpus all -e CUDA_VISIBLE_DEVICES=0 -v omnivoicetts_data:/app/persistent hangrylabs/omnivoicetts:latest
```

El comando está en una sola línea y se puede pegar directamente en Bash, PowerShell o el Símbolo del sistema de Windows. Docker crea automáticamente el volumen con nombre.

Después, abre:

- Interfaz web: [http://localhost:7861](http://localhost:7861)
- Documentación de la API: [http://localhost:7861/tts/docs](http://localhost:7861/tts/docs)
- [Ejemplos de idiomas y voces](https://hangry-labs.github.io/OmniVoiceTTS/examples/?lang=es)

El volumen `omnivoicetts_data` conserva modelos, ajustes y voces guardadas cuando se sustituye el contenedor o se actualiza la imagen. La imagen completa incluye los recursos del modelo y puede ejecutarse sin conexión después de descargarla.

## Más información

Consulta la [página completa del producto y la guía de instalación en español](https://hangrylabs.app/es/software/omnivoicetts). La referencia técnica completa se mantiene en el [README en inglés](README.md). Los errores y sugerencias pueden notificarse en [GitHub Issues](https://github.com/Hangry-Labs/OmniVoiceTTS/issues).
