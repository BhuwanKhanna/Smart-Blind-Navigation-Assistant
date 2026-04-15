from __future__ import annotations

import queue
import threading


class VoiceGuide:
    def __init__(self, rate: int = 175, language: str = "en") -> None:
        self.rate = rate
        self.language = language
        self.last_message = ""
        self.available = False
        self._queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._engine = self._init_engine()
        self._worker = threading.Thread(target=self._run_loop, daemon=True)
        self._worker.start()

    def configure(self, *, rate: int, language: str) -> None:
        self.rate = rate
        self.language = language

    def speak(self, text: str, language: str | None = None) -> None:
        selected_language = language or self.language
        self.last_message = text
        self._queue.put((text, selected_language))

    def _init_engine(self):
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
            self.available = True
            return engine
        except Exception:
            self.available = False
            return None

    def _run_loop(self) -> None:
        while True:
            text, language = self._queue.get()
            if not self.available or self._engine is None:
                print(f"[VOICE SIMULATION][{language}] {text}")
                continue
            try:
                self._set_voice(language)
                self._engine.setProperty("rate", self.rate)
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception as exc:
                print(f"[VOICE ERROR] {exc}")

    def _set_voice(self, language: str) -> None:
        if not self.available or self._engine is None:
            return
        voices = self._engine.getProperty("voices")
        preferred_tokens = {
            "en": ["english", "en_"],
            "hi": ["hindi", "india", "hi_"],
            "es": ["spanish", "es_"],
        }.get(language, ["english"])
        for voice in voices:
            name = f"{getattr(voice, 'name', '')} {getattr(voice, 'id', '')}".lower()
            if any(token in name for token in preferred_tokens):
                self._engine.setProperty("voice", voice.id)
                return
