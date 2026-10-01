import json
import os
import time
import wave
import tempfile
import threading

import pygame
import rclpy
from rclpy.node import Node

from std_msgs.msg import Bool, String, Empty
from sarai_msgs.srv import SetSpeech

from piper import PiperVoice, SynthesisConfig
from ament_index_python import get_package_share_directory


class TTS_Playsound(Node):

    def __init__(self):
        super().__init__("sarai_tts_playsound_node")

        self.speak_subscriber = self.create_subscription(
            String, "tts_input", self.topic_speak_callback, 10
        )

        # optional für manuelle Tests
        self.language_subscriber = self.create_subscription(
            String, "tts_language", self.topic_language_callback, 10
        )

        self.cancel_subscriber = self.create_subscription(
            Empty, "tts_cancel", self.cancel_callback, 10
        )

        self.reset_subscriber = self.create_subscription(
            Empty, "reset_drawing_session", self.cancel_callback, 10
        )

        self.display_robot_state_publisher = self.create_publisher(
            String, "display_robot_state", 10
        )
        self.recognizer_state_publisher = self.create_publisher(
            Bool, "recognizer_is_active", 10
        )

        self.speak_srv = self.create_service(
            SetSpeech, "speak", self.service_speak_callback
        )

        voice_dir = get_package_share_directory("sarai_tts_playsound") + "/voice_model"

        self.voice_paths = {
            "en": voice_dir + "/en_US-sam-medium.onnx",
            "de": voice_dir + "/de_DE-thorsten-medium.onnx",
        }

        self.syn_config_by_lang = {
            "en": SynthesisConfig(
                volume=1.0,
                length_scale=1.0,
                noise_scale=0.667,
                noise_w_scale=0.8,
                normalize_audio=False,
            ),
            "de": SynthesisConfig(
                volume=1.0,
                length_scale=1.0,
                noise_scale=0.667,
                noise_w_scale=0.8,
                normalize_audio=False,
            ),
        }

        self.voice_cache = {}
        self.current_lang = None
        self.voice = None
        self.syn_config = None

        self.voice_lock = threading.Lock()

        # latest only request handling
        self.request_lock = threading.Lock()
        self.pending_request = None
        self.request_event = threading.Event()
        self.request_version = 0
        self.shutdown_flag = False

        # initialize pygame mixer lazy
        self.mixer_ready = False
        self.mixer_spec = None
        self.mixer_lock = threading.Lock()

        self._load_language("en")
        self._set_robot_state("listening")

        self.worker_thread = threading.Thread(
            target=self._speech_worker, daemon=True
        )
        self.worker_thread.start()

    def _normalize_lang(self, lang: str) -> str:
        aliases = {
            "en": "en",
            "english": "en",
            "de": "de",
            "german": "de",
            "deutsch": "de",
        }
        lang = str(lang).lower()
        return aliases.get(lang, lang)

    def _load_language(self, lang: str) -> bool:
        lang = self._normalize_lang(lang)

        if lang not in self.voice_paths:
            self.get_logger().error(f"Unsupported TTS language: {lang}")
            return False

        with self.voice_lock:
            if lang not in self.voice_cache:
                self.get_logger().info(f"Loading TTS model: {lang}")
                self.voice_cache[lang] = PiperVoice.load(self.voice_paths[lang])

            self.voice = self.voice_cache[lang]
            self.syn_config = self.syn_config_by_lang[lang]
            self.current_lang = lang

        self.get_logger().info(f"TTS language switched to: {lang}")
        return True

    def _parse_request(self, raw: str) -> dict:
        default_lang = self.current_lang or "en"

        try:
            payload = json.loads(raw)
            if isinstance(payload, dict):
                text = " ".join(str(payload.get("text", "")).split())
                lang = self._normalize_lang(payload.get("lang", default_lang))
                return {"lang": lang, "text": text}
        except Exception:
            pass

        return {
            "lang": default_lang,
            "text": " ".join(str(raw).split()),
        }

    def _set_robot_state(self, state: str):
        robot_state_msg = String()
        robot_state_msg.data = state
        self.display_robot_state_publisher.publish(robot_state_msg)

        if state == "listening":
            recognizer_state_msg = Bool()
            recognizer_state_msg.data = True
            self.recognizer_state_publisher.publish(recognizer_state_msg)

    def _is_request_current(self, version: int) -> bool:
        with self.request_lock:
            return version == self.request_version

    def _stop_playback_now(self):
        with self.mixer_lock:
            try:
                if self.mixer_ready and pygame.mixer.get_init() is not None:
                    pygame.mixer.music.stop()
            except Exception:
                pass

    def _ensure_mixer(self, sample_rate: int, channels: int):
        wanted = (sample_rate, -16, channels)

        with self.mixer_lock:
            current = pygame.mixer.get_init()

            if current != wanted:
                try:
                    if current is not None:
                        pygame.mixer.music.stop()
                        pygame.mixer.quit()
                except Exception:
                    pass

                pygame.mixer.init(
                    frequency=sample_rate,
                    size=-16,
                    channels=channels,
                    buffer=4096,
                )
                self.mixer_ready = True
                self.mixer_spec = wanted

    def _write_wav(self, path: str, audio_bytes: bytes, sample_rate: int, channels: int):
        with wave.open(path, "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)  # int16
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_bytes)

    def speak(self, message: str, version: int):
        temp_path = None
        try:
            with self.voice_lock:
                voice = self.voice
                syn_config = self.syn_config

            if voice is None or syn_config is None:
                self.get_logger().error("TTS voice not initialized.")
                return

            sample_rate = None
            sample_channels = None
            audio_parts = []

            # synthesize in chunks for skip
            for chunk in voice.synthesize(message, syn_config=syn_config):
                if not self._is_request_current(version):
                    return

                if sample_rate is None:
                    sample_rate = chunk.sample_rate
                    sample_channels = chunk.sample_channels

                audio_parts.append(chunk.audio_int16_bytes)

            if not audio_parts:
                self.get_logger().warning("No audio chunks generated.")
                return

            if not self._is_request_current(version):
                return

            audio_bytes = b"".join(audio_parts)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                temp_path = tmp.name

            self._write_wav(temp_path, audio_bytes, sample_rate, sample_channels)

            if not self._is_request_current(version):
                return

            self._ensure_mixer(sample_rate, sample_channels)
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                if not self._is_request_current(version):
                    self._stop_playback_now()
                    return
                time.sleep(0.05)

        except Exception as e:
            self.get_logger().error(f"TTS playback failed: {e}")
            self._stop_playback_now()

        finally:
            self._stop_playback_now()
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def _speech_worker(self):
        while not self.shutdown_flag and rclpy.ok():
            if not self.request_event.wait(0.1):
                continue

            self.request_event.clear()

            while True:
                with self.request_lock:
                    request = self.pending_request
                    self.pending_request = None
                    current_version = self.request_version

                if request is None:
                    break

                if request["version"] != current_version:
                    continue

                if not request["text"]:
                    continue

                if not self._load_language(request["lang"]):
                    continue

                if not self._is_request_current(request["version"]):
                    continue

                self._set_robot_state("speaking")
                self.speak(request["text"], request["version"])
                self._set_robot_state("listening")

    def topic_speak_callback(self, msg):
        request = self._parse_request(msg.data)

        if not request["text"]:
            return

        with self.request_lock:
            self.request_version += 1
            request["version"] = self.request_version
            self.pending_request = request

        self._stop_playback_now()
        self.request_event.set()

    def cancel_callback(self, _msg):
        with self.request_lock:
            self.request_version += 1

        self._stop_playback_now()
        self._set_robot_state("listening")

    def topic_language_callback(self, msg):
        with self.request_lock:
            self.request_version += 1

        self._stop_playback_now()
        self._load_language(msg.data)
        self._set_robot_state("listening")

    def service_speak_callback(self, request, response):
        text = " ".join(str(request.message).split())

        if not text:
            return response

        with self.request_lock:
            self.request_version += 1
            self.pending_request = {
                "lang": self.current_lang or "en",
                "text": text,
                "version": self.request_version,
            }

        self._stop_playback_now()
        self.request_event.set()
        return response


def main(args=None):
    rclpy.init(args=args)
    node = TTS_Playsound()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown_flag = True
        node.request_event.set()
        node.worker_thread.join(timeout=1.0)
        node._stop_playback_now()

        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.quit()
        except Exception:
            pass

        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()