window.VOICE_EXAMPLES = [
  {
    "name": "Auto Voice",
    "mode": "Auto",
    "language": "English",
    "text": "OmniVoice can synthesize speech without a reference voice prompt.",
    "api": "{\"text\":\"Hello from OmniVoiceTTS.\",\"language\":\"English\",\"output_format\":\"mp3\"}"
  },
  {
    "name": "Voice Design",
    "mode": "Design",
    "language": "English",
    "text": "Use speaker attributes such as gender, age, pitch, style, accent, or dialect.",
    "api": "{\"text\":\"A designed OmniVoice sample.\",\"language\":\"English\",\"instruct\":\"female, low pitch, british accent\",\"output_format\":\"mp3\"}"
  },
  {
    "name": "Voice Cloning",
    "mode": "Clone",
    "language": "Any supported language",
    "text": "Provide a short reference audio clip and its transcript to clone the voice.",
    "api": "{\"text\":\"A cloned OmniVoice sample.\",\"language\":\"English\",\"ref_audio\":\"/data/ref.wav\",\"ref_text\":\"Transcript of the reference audio.\",\"output_format\":\"mp3\"}"
  }
];
