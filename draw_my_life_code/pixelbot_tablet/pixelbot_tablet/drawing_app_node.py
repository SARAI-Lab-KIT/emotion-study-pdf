import sys
import pygame
import os
import time
from datetime import datetime
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String, Empty
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import numpy as np
import cv2
from evdev import InputDevice, ecodes, list_devices
import threading
import json
from ament_index_python import get_package_share_directory
import threading
from evdev import InputDevice, ecodes
from enum import Enum
import random

# Turns off some checks to make testing faster:
#   - Allows quitting via Alt+F4
#   - Automatically selects "test" as name
#   - Mood Assessment doesn't require sliders to be moved
#   - Quitting doesn't require a password
#   - Some screens can be skipped with ENTER
DEBUG = True
# For testing when no Wacom device is connected
DISABLE_PRESSURE = True


def exit_program():
    # for some reason, without this, alt+f4 closes another window as well
    time.sleep(0.2)
    pygame.quit()
    rclpy.shutdown()
    sys.exit()


def check_quit(event):
    # checks for Alt+F4
    if DEBUG and event.type == pygame.QUIT:
        exit_program()


class Emotions(Enum):
    EXCITEMENT = 1
    CONTENTMENT = 2
    ANGER = 3
    SADNESS = 4
    NEUTRAL = 5


class Language(Enum):
    """
    classes with translated text:
        - StartScreenDocumentation
        - PopupWindow
        - DrawingApplicationNode
    """

    English = "en"
    German = "de"


class SessionType(Enum):
    Adult = "adult"
    Child = "child"


class Message:
    @classmethod
    def get(cls, message):
        if message not in cls.messages:
            print(f"Error: {message} does not exist!")
            return message  # display the key that doesn't exist
        if cls.current_lang.value not in cls.messages[message]:
            print(
                f"Error: {message} was not translated to {cls.current_lang}!")
            # fall back to english
            cls.messages[message][Language.English.value]

        return cls.messages[message][cls.current_lang.value]

    current_lang = Language.English  # default language
    messages = {
        "msg_exit": {
            "en": "Do you really want to exit?",
            "de": "Möchtest du aufhören?"
        },
        "msg_password": {
            "en": "Enter password:",
            "de": "Passwort eingeben"
        },
        "msg_name": {
            "en": "Enter the Participant-ID!",
            "de": "Teilnehmer-ID eingeben!"
        },
        "error_message_empty_name": {
            "en": "Participant-ID must not be empty!",
            "de": "Teilnehmer-ID darf nicht leer sein!"
        },
        "msg_save": {
            "en": "Do you want to stop drawing?",  # maybe change this?
            "de": "Ist dein Bild fertig?"
        },
        "msg_study_mood_induction_neutral": {
            "en": ("Please recall a typical event from your daily routine, such as getting ready in the morning.\n"
                   "This event must be specific and distinct.\n"
                   "Try to remember this event in as much detail as possible.\n"
                   "Think about what happened, where you were, and who was present.\n"
                   "Spend the next three minutes focusing on this memory and reliving this event you experienced."),

            "de": ("Versuche dich an ein typisches Ereignis aus deinem Alltag zu erinnern, zum Beispiel, wie du zur Schule gehst.\n"
                   "Dieses Ereignis soll konkret und eindeutig sein.\n"
                   "Versuche, dich so genau wie möglich an dieses Ereignis zu erinnern.\n"
                   "Überlege, was passiert ist, wo du warst und wer dabei war.\n"
                   "Nimm dir die nächsten drei Minuten Zeit, um dich auf diese Erinnerung zu konzentrieren und dieses Erlebnis noch einmal in Gedanken durchzuleben."),
        },
        "msg_study_mood_induction_sentence_1": {
            "en": "Please recall a time in your life in which you felt very ",
            "de": "Denke an eine Zeit in deinem Leben,\nin der du dich sehr "
        },
        "msg_study_mood_induction": {
            "en": (".\n"
                   "This event does not have to be extraordinary, but it must be specific and distinct.\n"
                   "Try to remember this event in as much detail as possible.\n"
                   "Think about what happened, where you were, who was present, and how you felt at the time.\n"
                   "Spend the next three minutes focusing on this memory and reliving the emotions you experienced."),

            "de": (" gefühlt hast.\n"
                   "Dieses Erlebnis muss nicht außergewöhnlich sein, aber es soll konkret und eindeutig sein.\n"
                   "Versuche, dich so genau wie möglich an dieses Erlebnis zu erinnern.\n"
                   "Überlege, was passiert ist, wo du warst, wer dabei war und wie du dich damals gefühlt hast.\n"
                   "Nimm dir die nächsten drei Minuten Zeit, um dich auf diese Erinnerung zu konzentrieren und die Gefühle noch einmal zu erleben.")
        },
        "msg_study_end": {
            "en": ("Thank you for participating in this study!\n"
                   "Please leave this room and go to the supervisor.\n"),
            "de": ("Vielen Dank für die Teilnahme an dieser Studie!\n"
                   "Verlasse nun bitte den Raum und gehe zur Aufsichtsperson.\n")
        },
        "msg_slider_error": {
            "en": "Please move both sliders!",
            "de": "Bewege bitte beide Slider!"
        },
        "title_popup": {
            "en": "Wait!",
            "de": "Warte!"
        },
        "choice_yes": {
            "en": "Yes",
            "de": "Ja"
        },
        "choice_no": {
            "en": "No",
            "de": "Nein"
        },
        "path_documentation": {
            "en": "Documentation Image.png",
            "de": "Documentation Image_german.png"
        },
        "mood_excited": {
            "en": "excited",
            "de": "begeistert"
        },
        "mood_angry": {
            "en": "angry",
            "de": "wütend"
        },
        "mood_contentment": {
            "en": "content",
            "de": "zufrieden"
        },
        "mood_sad": {
            "en": "sad",
            "de": "traurig"
        },
        "button_continue": {
            "en": "Continue",
            "de": "Weiter"
        },
        "button_skip": {
            "en": "Skip",
            "de": "Überspringen"
        },
        "msg_tts_greeting": {
            "en": "Hello, I am PixelBot! I will guide you through this study. If there are any problems, please ask the supervisor.",
            "de": "Hallo, ich bin PixelBot! Ich werde dich durch dieses Experiment leiten. Falls es Probleme gibt, frage bitte einen Mitarbeiter."
        },
        "msg_start_study": {
            "en": "Press 'Continue' to start the study!",
            "de": "Auf 'Weiter' drücken,\n um mit dem Experiment zu beginnen"
        },
        "msg_session_type": {
            "en": "Session type: adult or child?",
            "de": "Session-Typ: adult oder child?"
        },
        "error_session_type": {
            "en": "Please enter adult or child.",
            "de": "Bitte adult oder child eingeben."
        },
        "msg_emotion_order": {
            "en": "Enter 3 emotions, comma separated",
            "de": "3 Emotionen mit Komma eingeben"
        },
        "error_emotion_order": {
            "en": "Use exactly 3 different emotions from the list.",
            "de": "Bitte genau 3 verschiedene Emotionen aus der Liste eingeben."
        },
        "msg_slider_error_valence": {
            "en": "Please move the slider!",
            "de": "Bewege bitte den Slider!"
        },
        "msg_valence_label": {
            "en": "How sad or happy are you feeling right now?",
            "de": "Wie traurig oder glücklich fühlst du dich gerade?"
        },
        "msg_arousal_label": {
            "en": "How calm or alert are you feeling right now?",
            "de": "Wie ruhig oder aufgeregt fühlst du dich gerade?"
        },
        "msg_small_break": {
            "en": "Small break. Please go visit the supervisor.\nPress Continue to start the next round.",
            "de": "Kurze Pause. Bitte gehe zur Aufsichtsperson.\nDrücke Weiter, um die nächste Runde zu starten."
        },
        "msg_mood_repair_draw_robot": {
            "en": "Your final task is to draw PixelBot.\nPress the save button when you are finished.",
            "de": "Male zum Abschluss bitte PixelBot.\nWenn du fertig bist, drücke den \"Speichern\" Knopf."
        },
        "msg_mood_repair_discussion": {
            "en": "Now take a short relaxed moment with the supervisor.",
            "de": "Nimm dir nun einen ruhigen Moment mit der Aufsichtsperson."
        },
        "msg_child_mood_induction_neutral": {
            "en": "Think about something you often do, like getting ready or going to school. Try to picture it in your mind for the next few minutes.",
            "de": "Denke an etwas, das du oft machst, zum Beispiel, wie du deine Zähne putzt oder zur Schule gehst.\nDenke in den nächsten 3 Minuten daran."
        },
        "msg_child_mood_induction_sentence_1": {
            "en": "Think about a time when you felt very ",
            "de": "Denke an eine Situation, in der du dich sehr "
        },
        "msg_child_mood_induction": {
            "en": ". Try to remember what happened and how it felt.\nKeep thinking about this moment for the next few minutes.",
            "de": " gefühlt hast.\nVersuche dich zu erinnern, was passiert ist\nund wie es sich angefühlt hat.\nDenke in den nächsten 3 Minuten daran."
        },
    }


def publish_tts_request(publisher, text: str, language):
    payload = {
        "lang": language.value if isinstance(language, Language) else str(language),
        "text": " ".join(text.split()),
    }

    message = String()
    message.data = json.dumps(payload, ensure_ascii=False)
    publisher.publish(message)


def publish_tts_cancel(publisher):
    publisher.publish(Empty())


def parse_session_type(raw_text: str):
    value = str(raw_text).strip().lower()
    if value in ("adult", "adults", "erwachsene", "erwachsen"):
        return SessionType.Adult
    if value in ("child", "children", "kid", "kids", "kind", "kinder"):
        return SessionType.Child
    return None


def parse_emotion_sequence(raw_text: str):
    aliases = {
        "e": Emotions.EXCITEMENT,
        "excited": Emotions.EXCITEMENT,
        "excitement": Emotions.EXCITEMENT,
        "begeistert": Emotions.EXCITEMENT,
        "begeisterung": Emotions.EXCITEMENT,
        "c": Emotions.CONTENTMENT,
        "calm": Emotions.CONTENTMENT,
        "contentment": Emotions.CONTENTMENT,
        "content": Emotions.CONTENTMENT,
        "serene": Emotions.CONTENTMENT,
        "ruhig": Emotions.CONTENTMENT,
        "a": Emotions.ANGER,
        "angry": Emotions.ANGER,
        "anger": Emotions.ANGER,
        "wütend": Emotions.ANGER,
        "wuetend": Emotions.ANGER,
        "s": Emotions.SADNESS,
        "sad": Emotions.SADNESS,
        "sadness": Emotions.SADNESS,
        "traurig": Emotions.SADNESS,
        "n": Emotions.NEUTRAL,
        "neutral": Emotions.NEUTRAL,
        "normal": Emotions.NEUTRAL,
    }

    parts = [part.strip().lower()
             for part in str(raw_text).replace(";", ",").split(",")]
    parts = [part for part in parts if part]

    emotions = []
    for part in parts:
        if part not in aliases:
            return None
        emotions.append(aliases[part])

    if len(emotions) != 3:
        return None
    if len(set(emotions)) != 3:
        return None

    return emotions


class Stroke:
    def __init__(self, x, y, pressure, pen_color=None, pen_size=None, timestamps=None, tilt_x=None, tilt_y=None):
        self.x = np.array(x)
        self.y = np.array(y)
        self.pressure = np.array(pressure, dtype=float)

        point_count = len(self.x)

        if tilt_x is None:
            tilt_x = [np.nan] * point_count
        if tilt_y is None:
            tilt_y = [np.nan] * point_count
        self.tilt_x = np.array(tilt_x, dtype=float)
        self.tilt_y = np.array(tilt_y, dtype=float)

        self.pen_color = tuple(pen_color) if pen_color is not None else None
        self.pen_size = pen_size
        self.timestamps = np.array(
            timestamps if timestamps is not None else [])


# main UI colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (150, 150, 150)
BLUE = (0, 120, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)

# Other define
BLUE_BORDER_THICKNESS = 5
DRAW, ERASE = 0, 1


def count_ink_pixels(surface):
    """
    Counts non-white pixels on the drawing surface.
    """

    surface_np = pygame.surfarray.array3d(surface)
    white = np.array(WHITE, dtype=surface_np.dtype)

    # A pixel is ink if at least one channel differs from white
    ink_mask = np.any(surface_np != white, axis=2)

    return int(np.count_nonzero(ink_mask))


class WacomPressureReader:
    """
    Robust Wacom reader.

    Reconnects automatically if /dev/input/eventX disappears.
    Selects the Wacom Pen device by capabilities, not only by name.
    """

    def __init__(self, require_tilt=True, reconnect_delay_s=0.5):
        self.require_tilt = require_tilt
        self.reconnect_delay_s = reconnect_delay_s
        self.device = None
        self.device_path = None
        self.device_name = None
        self.pressure = np.nan
        self.tilt_x = np.nan
        self.tilt_y = np.nan
        self.last_event_time = 0.0
        self.connected = False
        self.running = True
        self.lock = threading.Lock()

        self.thread = threading.Thread(target=self.read_loop, daemon=True)
        self.thread.start()

    def _device_has_required_capabilities(self, dev):
        caps = dev.capabilities(absinfo=False)
        abs_codes = set(caps.get(ecodes.EV_ABS, []))

        has_pressure = ecodes.ABS_PRESSURE in abs_codes
        has_tilt_x = ecodes.ABS_TILT_X in abs_codes
        has_tilt_y = ecodes.ABS_TILT_Y in abs_codes

        if not has_pressure:
            return False, has_pressure, has_tilt_x, has_tilt_y

        if self.require_tilt and not (has_tilt_x and has_tilt_y):
            return False, has_pressure, has_tilt_x, has_tilt_y

        return True, has_pressure, has_tilt_x, has_tilt_y

    def _find_wacom_pen_device(self):
        """
        Find the correct Wacom Pen device.

        We prefer a device that:
        - has Wacom in the name
        - has Pen in the name
        - provides ABS_PRESSURE
        - provides ABS_TILT_X and ABS_TILT_Y
        """
        best = None

        for path in list_devices():
            try:
                dev = InputDevice(path)
                name = dev.name or ""

                valid, has_pressure, has_tilt_x, has_tilt_y = (
                    self._device_has_required_capabilities(dev)
                )

                is_wacom = "Wacom" in name
                is_pen = "Pen" in name or "pen" in name

                if not is_wacom or not valid:
                    dev.close()
                    continue

                score = 0
                if is_pen:
                    score += 10
                if has_pressure:
                    score += 5
                if has_tilt_x:
                    score += 2
                if has_tilt_y:
                    score += 2

                if best is None or score > best["score"]:
                    if best is not None:
                        try:
                            best["dev"].close()
                        except Exception:
                            pass

                    best = {
                        "score": score,
                        "path": path,
                        "dev": dev,
                        "name": name,
                        "has_pressure": has_pressure,
                        "has_tilt_x": has_tilt_x,
                        "has_tilt_y": has_tilt_y,
                    }
                else:
                    dev.close()

            except Exception:
                continue

        return best

    def _mark_disconnected(self):
        with self.lock:
            self.connected = False
            self.device = None
            self.device_path = None
            self.device_name = None
            self.pressure = np.nan
            self.tilt_x = np.nan
            self.tilt_y = np.nan
            self.last_event_time = 0.0

    def read_loop(self):
        """
        Main reading loop.

        This method must never die permanently.
        If the Wacom device disappears, it reconnects.
        """
        while self.running:
            selected = self._find_wacom_pen_device()

            if selected is None:
                self._mark_disconnected()
                print("Wacom reader: no suitable Wacom Pen device found. Retrying...")
                time.sleep(self.reconnect_delay_s)
                continue

            dev = selected["dev"]

            with self.lock:
                self.device = dev
                self.device_path = selected["path"]
                self.device_name = selected["name"]
                self.connected = True
                self.pressure = np.nan
                self.tilt_x = np.nan
                self.tilt_y = np.nan
                self.last_event_time = 0.0

            print(
                "Using Wacom pressure device:",
                selected["path"],
                "->",
                selected["name"],
                f"(pressure={selected['has_pressure']}, "
                f"tilt_x={selected['has_tilt_x']}, "
                f"tilt_y={selected['has_tilt_y']})"
            )

            try:
                for event in dev.read_loop():
                    if not self.running:
                        break

                    if event.type == ecodes.EV_ABS:
                        now = time.time()

                        with self.lock:
                            self.last_event_time = now

                            if event.code == ecodes.ABS_PRESSURE:
                                self.pressure = float(event.value)
                            elif event.code == ecodes.ABS_TILT_X:
                                self.tilt_x = float(event.value)
                            elif event.code == ecodes.ABS_TILT_Y:
                                self.tilt_y = float(event.value)

            except OSError as e:
                print(
                    f"Wacom reader lost device {self.device_path}: {e}. "
                    "Reconnecting..."
                )

            except Exception as e:
                print(f"Wacom reader error: {e}. Reconnecting...")

            finally:
                try:
                    dev.close()
                except Exception:
                    pass

                self._mark_disconnected()
                time.sleep(self.reconnect_delay_s)

    def wait_until_connected(self, timeout_s=5.0):
        start = time.time()

        while time.time() - start < timeout_s:
            with self.lock:
                if self.connected:
                    return True

            time.sleep(0.05)

        return False

    def get_state(self, max_age_s=0.75):
        """
        Returns the current pressure/tilt state.

        valid=True means:
        - device is connected
        - latest event is fresh
        - pressure is finite and > 0
        - tilt is finite if require_tilt=True
        """
        now = time.time()

        with self.lock:
            connected = self.connected
            pressure = self.pressure
            tilt_x = self.tilt_x
            tilt_y = self.tilt_y
            last_event_time = self.last_event_time
            device_path = self.device_path
            device_name = self.device_name

        event_age = now - last_event_time if last_event_time > 0 else np.inf

        pressure_ok = (
            connected
            and np.isfinite(pressure)
            and pressure > 0
            and event_age <= max_age_s
        )

        if self.require_tilt:
            tilt_ok = np.isfinite(tilt_x) and np.isfinite(tilt_y)
        else:
            tilt_ok = True

        valid = pressure_ok and tilt_ok

        return {
            "valid": valid,
            "connected": connected,
            "pressure": pressure if pressure_ok else np.nan,
            "tilt_x": tilt_x if np.isfinite(tilt_x) else np.nan,
            "tilt_y": tilt_y if np.isfinite(tilt_y) else np.nan,
            "event_age": event_age,
            "device_path": device_path,
            "device_name": device_name,
        }

    def stop(self):
        self.running = False

        try:
            if self.device is not None:
                self.device.close()
        except Exception:
            pass


# class: Button
class IconButton:
    def __init__(
        self, undo_manager, camera, image_surface, position, palette=None, image_surface_disabled=None, type=None
    ):
        self.undo_manager = undo_manager
        self.camera = camera
        self.image = image_surface
        self.image_gray = image_surface_disabled
        self.position = position
        self.rect = self.image.get_rect(topleft=position)
        self.palette = palette
        self.type = type

    # display icons of button in menu bar with fitting color and fitting border color
    def display(self, surface, border_color):
        if self.image_gray is not None:
            if self.undo_manager.current_index_surface_stack == 1 and self.type == "undo":
                surface.blit(self.image_gray, self.position)
            elif (
                self.undo_manager.current_index_surface_stack == len(
                    self.undo_manager.surface_stack)
                and self.type == "redo"
            ):
                surface.blit(self.image_gray, self.position)
            elif self.camera.zoom_scale == self.camera.min_zoom and self.type == "zoom out":
                surface.blit(self.image_gray, self.position)
            elif self.camera.zoom_scale == self.camera.max_zoom and self.type == "zoom in":
                surface.blit(self.image_gray, self.position)
            else:
                surface.blit(self.image, self.position)
        else:
            surface.blit(self.image, self.position)

        pygame.draw.rect(
            surface, border_color, self.rect, width=2, border_radius=int(min(self.rect.height, self.rect.width) / 16)
        )

    # check if user is hovering over icon button
    def check_click(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)

    # show option palette when icon button has been clicked
    def handle_click(self):
        if self.palette:
            self.palette.change_visibility()


class Button:
    def __init__(self, image_surface, position, active):
        self.image = image_surface
        self.position = position
        self.rect = self.image.get_rect(topleft=position)
        self.active = active

    # display icons of button in menu bar with fitting color and fitting border color
    def display(self, surface):
        surface.blit(self.image, self.position)
        border_color = BLUE if self.active else BLACK
        pygame.draw.rect(
            surface, border_color, self.rect, width=2, border_radius=int(min(self.rect.height, self.rect.width) / 16)
        )

    # check if user is hovering over icon button
    def check_click(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)


# class: Palette


class Palette:
    def __init__(self, main_screen, options, type, pencil, window_width, pencil_size_list=None):
        self.main_screen = main_screen
        self.options = options
        self.type = type
        self.pencil = pencil
        self.visible = False
        self.pencil_size_list = pencil_size_list
        self.WINDOW_WIDTH = window_width

    # change visibility of palette instance
    def change_visibility(self):
        self.visible = not self.visible

    # hide palette
    def hide(self):
        self.visible = False

    # display option palette(color or pencil size)
    def display(self, surface, border_color):
        if self.visible:
            if self.type == "color":
                for option, position in self.options:
                    rect = pygame.Rect(
                        *position, 1.5 / 100 * self.WINDOW_WIDTH, 1.5 / 100 * self.WINDOW_WIDTH)
                    pygame.draw.rect(surface, option, rect, border_radius=int(
                        min(rect.height, rect.width) / 16))
                    pygame.draw.rect(
                        surface, border_color, rect, width=2, border_radius=int(min(rect.height, rect.width) / 16)
                    )
            elif self.type == "size":
                for index in range(len(self.options)):
                    # Display the pencil image
                    self.main_screen.blit(
                        self.pencil_size_list[index], self.options[index][1])
                    # Draw the rectanle around the pencil image
                    rect = pygame.Rect(
                        *self.options[index][1], 2.5 / 100 *
                        self.WINDOW_WIDTH, 2.5 / 100 * self.WINDOW_WIDTH
                    )
                    pygame.draw.rect(
                        surface, border_color, rect, width=2, border_radius=int(min(rect.height, rect.width) / 16)
                    )

    # check what user chooses in palette and set choosen option
    def handle_palette_click(self, mouse_position):
        if self.visible:
            for option, position in self.options:
                if self.type == "color":
                    option_rectangle = pygame.Rect(
                        position, (1.5 / 100 * self.WINDOW_WIDTH,
                                   1.5 / 100 * self.WINDOW_WIDTH)
                    )
                    if option_rectangle.collidepoint(mouse_position):
                        self.pencil.color = option
                        self.hide()
                        break
                elif self.type == "size":
                    option_rectangle = pygame.Rect(
                        position, (2.5 / 100 * self.WINDOW_WIDTH,
                                   2.5 / 100 * self.WINDOW_WIDTH)
                    )
                    if option_rectangle.collidepoint(mouse_position):
                        self.pencil.tool_size = option
                        self.hide()
                        break


# class: Tool
class Tool:
    def __init__(self, camera, main_screen, color, tool_size, menu_height):
        self.camera = camera
        self.main_screen = main_screen
        self.color = color
        self.tool_size = tool_size
        self.menu_height = menu_height
        self.active = False
        self.last_position = None
        self.last_add_point_time = None
        self.time_threshold = 3.5
        self.button_down_time = None
        self.ink_pixel_before_erased = None

    # method to draw a rather smooth line
    def draw_smooth_line(self, surface, start_position, end_position):
        if start_position == end_position:
            pygame.draw.circle(surface, self.color,
                               start_position, self.tool_size // 2)
        else:
            pygame.draw.line(surface, self.color, start_position,
                             end_position, self.tool_size)
            pygame.draw.circle(surface, self.color,
                               start_position, self.tool_size // 2.5)
            pygame.draw.circle(surface, self.color,
                               end_position, self.tool_size // 2.5)

    # method to handle drawing, erasing, moving the drawing and capturing stoke coordinates
    def handle_event(
        self,
        event,
        surface,
        pencil,
        eraser,
        move_tool,
        active_tool,
        menu_height,
        current_stroke,
        activity_start_time,
        current_pressure=None,
        current_tilt_x=None,
        current_tilt_y=None,
    ):
        number_erased_pixels = 0
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if event.pos[1] < menu_height:
                self.active = False
                self.last_position = None
                if active_tool == eraser:
                    self.ink_pixel_before_erased = None
                return current_stroke, number_erased_pixels

            self.active = True
            self.last_position = event.pos
            self.button_down_time = time.time()

            if active_tool == eraser:
                self.ink_pixel_before_erased = count_ink_pixels(surface)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.active = False
            self.last_position = None

            if active_tool == eraser and self.ink_pixel_before_erased is not None:
                ink_pixel_after_erased = count_ink_pixels(surface)
                number_erased_pixels = self.ink_pixel_before_erased - ink_pixel_after_erased
                self.ink_pixel_before_erased = None

        elif event.type == pygame.MOUSEMOTION and self.active:
            mouse_position = pygame.math.Vector2(event.pos)

            if active_tool == move_tool:
                current_mouse_position = mouse_position
                difference = (self.last_position -
                              current_mouse_position) / self.camera.zoom_scale
                self.camera.offset += difference
                self.last_position = current_mouse_position
                self.camera.limit_offset()

            elif active_tool in (pencil, eraser):
                adjusted_position = (
                    mouse_position / self.camera.zoom_scale
                    + self.camera.offset
                    - pygame.math.Vector2(0, self.menu_height) /
                    self.camera.zoom_scale
                )

                if self.last_position and event.pos[1] >= menu_height:
                    adjusted_last = (
                        pygame.math.Vector2(
                            self.last_position) / self.camera.zoom_scale
                        + self.camera.offset
                        - pygame.math.Vector2(0, self.menu_height) /
                        self.camera.zoom_scale
                    )
                    self.draw_smooth_line(
                        surface, adjusted_last, adjusted_position)
                    self.camera.drawing_version += 1

                    # Recording of stroke color, size and points
                    if active_tool in (pencil, eraser):
                        tool_type = "erase" if active_tool == eraser else "draw"
                        self.last_add_point_time = time.time()
                        if current_stroke == None:
                            current_stroke = {
                                "tool_type": tool_type,
                                "pen_color": self.color,
                                "pen_size": self.tool_size,
                                "points": [
                                    (int(adjusted_last.x), int(adjusted_last.y)),
                                    (int(adjusted_position.x),
                                     int(adjusted_position.y)),
                                ],
                                "timestamps": [
                                    self.button_down_time - activity_start_time,
                                    self.last_add_point_time - activity_start_time,
                                ],
                            }
                            if current_pressure is not None:
                                current_stroke["pressure_values"] = [
                                    current_pressure, current_pressure]
                            if current_tilt_x is not None:
                                current_stroke["tilt_x_values"] = [
                                    current_tilt_x, current_tilt_x]
                            if current_tilt_y is not None:
                                current_stroke["tilt_y_values"] = [
                                    current_tilt_y, current_tilt_y]
                        else:
                            current_stroke["points"].append(
                                (int(adjusted_position.x), int(adjusted_position.y)))
                            current_stroke["timestamps"].append(
                                self.last_add_point_time - activity_start_time)
                            if current_pressure is not None:
                                current_stroke["pressure_values"].append(
                                    current_pressure)
                            if current_tilt_x is not None:
                                current_stroke.setdefault(
                                    "tilt_x_values", []).append(current_tilt_x)
                            if current_tilt_y is not None:
                                current_stroke.setdefault(
                                    "tilt_y_values", []).append(current_tilt_y)

                self.last_position = mouse_position

        return current_stroke, number_erased_pixels

    # check if user hasnt drawn in the last time threshold
    def check_inactivity(self):
        if self.last_add_point_time and time.time() - self.last_add_point_time > self.time_threshold:
            self.last_add_point_time = None
            return True
        else:
            return False

    # display fitting eraser border, depending on zoom
    def display_eraser_border(self, active_tool, eraser, menu_height):
        if active_tool == eraser:
            mouse_position = pygame.mouse.get_pos()
            if mouse_position[1] >= menu_height + 5:
                zoom = self.camera.zoom_scale
                radius = int(self.tool_size * zoom / 2.5)
                pygame.draw.circle(self.main_screen, BLACK,
                                   mouse_position, radius + 2, width=2)
                pygame.draw.circle(self.main_screen, WHITE,
                                   mouse_position, radius, width=2)

    # display fitting tool icon border color, depends on wether tool is activated
    def display_borders_tool(self, rectangle, active_tool):
        if self == active_tool:
            pygame.draw.rect(
                self.main_screen,
                BLUE,
                rectangle,
                width=2,
                border_radius=int(min(rectangle.height, rectangle.width) / 16),
            )
        else:
            pygame.draw.rect(
                self.main_screen,
                GRAY,
                rectangle,
                width=2,
                border_radius=int(min(rectangle.height, rectangle.width) / 16),
            )


# class: Start screen
class StartScreenDocumentation:
    def __init__(
        self,
        screen,
        welcome_image_path,
        button_image_path,
        exit_image_path,
        german_flag_path,
        english_flag_path,
        background_image_path,
        window_height,
        window_width,
        clock,
        undo_manager,
        camera,
        save_manager,
        greeting_message_publisher,
    ):
        self.window_height = window_height
        self.window_width = window_width
        self.clock = clock
        self.undo_manager = undo_manager
        self.camera = camera
        self.save_manager = save_manager
        self.greeting_message_publisher = greeting_message_publisher
        self.screen = screen
        self.startscreen_done = False
        self.documentation_done = False
        self.session_type = SessionType.Adult
        self.selected_emotions = [Emotions.EXCITEMENT,
                                  Emotions.ANGER, Emotions.SADNESS]

        welcome_image_size = (self.window_width // 2, self.window_height // 3)
        self.welcome_image = pygame.transform.smoothscale(
            pygame.image.load(
                welcome_image_path).convert_alpha(), welcome_image_size
        )
        self.start_button_image = pygame.transform.smoothscale(
            pygame.image.load(button_image_path).convert_alpha(
            ), (self.window_width // 10, self.window_height // 10)
        )
        self.background_image = pygame.transform.smoothscale(
            pygame.image.load(background_image_path).convert_alpha(
            ), (self.window_width, self.window_height)
        )

        self.start_button_position = (
            self.window_width // 2 - self.start_button_image.get_width() // 2,
            self.window_height // 2 + self.start_button_image.get_height() // 2,
        )
        self.start_button = IconButton(
            self.undo_manager, self.camera, self.start_button_image, (
                self.start_button_position)
        )

        self.exit_button_position = (
            self.window_width - self.window_width // 30, 2 / 100 * self.window_height)
        self.exit_button = pygame.transform.smoothscale(
            pygame.image.load(exit_image_path).convert_alpha(),
            (2 / 100 * self.window_width, 2 / 100 * self.window_width),
        )

        germany_pos = (self.window_width - 50 - 25,
                       5 / 100 * self.window_width)
        self.germany_button = Button(
            pygame.image.load(
                german_flag_path), germany_pos, Message.current_lang == Language.German
        )
        english_pos = (self.window_width - 2 * 50 - 25 -
                       10, 5 / 100 * self.window_width)
        self.english_button = Button(
            pygame.image.load(
                english_flag_path), english_pos, Message.current_lang == Language.English
        )

    # display documentation and handle close button

    def show_documentation(self):
        documentation_image = pygame.transform.smoothscale(
            pygame.image.load(
                os.path.join("src", "pixelbot_tablet", "images",
                             Message.get("path_documentation"))
            ).convert(),
            (self.window_width, self.window_height),
        )
        self.documentation_done = False
        while not self.documentation_done:
            self.clock.tick(10)
            for event in pygame.event.get():
                check_quit(event)
                if event.type == pygame.MOUSEBUTTONUP:
                    if self.exit_button.get_rect(
                        topleft=(self.window_width - self.window_width //
                                 20, 6 / 100 * self.window_height)
                    ).collidepoint(event.pos):
                        self.documentation_done = True
                # close documentation with enter
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    self.documentation_done = True

            self.screen.blit(documentation_image, (0, 0))
            self.screen.blit(
                self.exit_button, (self.window_width - self.window_width //
                                   20, 6 / 100 * self.window_height)
            )
            pygame.display.update()

    # display startscreen with hover effect of start button
    def display(self, study_mode=False):
        self.screen.fill(WHITE)
        self.screen.blit(self.background_image, (0, 0))
        self.screen.blit(
            self.welcome_image,
            (
                self.window_width // 2 - self.welcome_image.get_width() // 2,
                self.window_height // 2 - self.welcome_image.get_height() // 2 -
                self.window_height // 8,
            ),
        )
        hovered = self.start_button.check_click(pygame.mouse.get_pos())
        if hovered:
            self.start_button.display(self.screen, BLUE)
        elif not hovered:
            self.start_button.display(self.screen, BLACK)
        if not study_mode:
            self.screen.blit(self.exit_button, self.exit_button_position)
            self.germany_button.display(self.screen)
            self.english_button.display(self.screen)

    # handle clicks in startscreen
    def handle_setup_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP:
            if self.start_button.check_click(event.pos):
                self.startscreen_done = True
            elif self.exit_button.get_rect(topleft=self.exit_button_position).collidepoint(event.pos):
                popup_confirmation = PopupWindow(
                    self.screen, pygame.font.SysFont("arial", 25), self.clock)
                answer = popup_confirmation.ask_confirmation(
                    Message.get("msg_exit"))
                if answer == "yes":
                    # don't ask for the password if debug mode is enabled
                    if DEBUG:
                        return True

                    popup_close = PopupWindow(
                        self.screen, pygame.font.SysFont("arial", 25), self.clock)
                    password = popup_close.handle_input(
                        Message.get("msg_password"), is_password=True)
                    if password == "1248":
                        # Add clean closing of all the nodes
                        return True
            elif self.germany_button.check_click(event.pos):
                Message.current_lang = Language.German
                self.germany_button.active = True
                self.english_button.active = False
            elif self.english_button.check_click(event.pos):
                Message.current_lang = Language.English
                self.germany_button.active = False
                self.english_button.active = True
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.startscreen_done = True
        return False

    # Returns True if Start Button was pressed
    def handle_start_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP:
            if self.start_button.check_click(event.pos):
                return True
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            return True
        return False

    # run start screen, show documentation once and ask for child name
    def run_start(self):
        self.startscreen_done = False
        done = False
        while not done:
            self.clock.tick(10)
            for event in pygame.event.get():
                check_quit(event)
                done = done or self.handle_start_event(event)
            self.display(study_mode=True)
            pygame.display.update()

        # TODO: Maybe we can print out the documentation?
        self.show_documentation()

    def run_setup(self) -> bool:
        self.startscreen_done = False
        while not self.startscreen_done:
            self.clock.tick(10)
            for event in pygame.event.get():
                check_quit(event)
                if self.handle_setup_event(event):
                    return False
            self.display()
            pygame.display.update()

        if DEBUG:
            self.child_name = "test"
            self.session_type = SessionType.Adult
            self.selected_emotions = [
                Emotions.EXCITEMENT, Emotions.ANGER, Emotions.SADNESS]
        else:
            popup = PopupWindow(
                self.screen, pygame.font.SysFont("arial", 25), self.clock)
            self.child_name = popup.handle_input(
                Message.get("msg_name"), max_chars=12)

            # while True:
            #    popup = PopupWindow(
            #        self.screen, pygame.font.SysFont("arial", 25), self.clock)
            #    raw_session_type = popup.handle_input(
            #        Message.get("msg_session_type"), max_chars=16)
            #    parsed_session_type = parse_session_type(raw_session_type)
            #    if parsed_session_type is not None:
            #        self.session_type = parsed_session_type
            #        break
            #    print(Message.get("error_session_type"))

            while True:
                popup = PopupWindow(
                    self.screen, pygame.font.SysFont("arial", 22), self.clock)
                raw_emotions = popup.handle_input(
                    Message.get("msg_emotion_order"), max_chars=80)
                parsed_emotions = parse_emotion_sequence(raw_emotions)
                if parsed_emotions is not None:
                    self.selected_emotions = parsed_emotions
                    break
                print(Message.get("error_emotion_order"))

        self.save_manager.create_saving_folder(self.child_name)
        return True


# class: Undo manager: manages undo and redo functionality
class UndoManager:
    def __init__(self):
        self.surface_stack = []
        self.current_index_surface_stack = 0

        self.stroke_data_stack = []
        self.current_index_stroke_data_stack = 0

        self.last_drawing_action = None

        self.undone_erased_stroke_list = []

    def reset(self):
        self.surface_stack.clear()
        self.stroke_data_stack.clear()
        self.undone_erased_stroke_list.clear()
        self.current_index_surface_stack = 0
        self.current_index_stroke_data_stack = 0
        self.last_drawing_action = None

    # add copy of current drawing interface to surface_stack.
    def append_drawing(self, surface):
        # delete all newer drawings than current drawing when user draws something new
        if self.current_index_surface_stack < len(self.surface_stack):
            self.surface_stack = self.surface_stack[:
                                                    self.current_index_surface_stack]

        self.surface_stack.append(surface.copy())
        self.current_index_surface_stack += 1

    def append_stroke(self, stroke):
        # if user draws something new, you can't redo
        if self.current_index_stroke_data_stack < len(self.stroke_data_stack):
            # store the undone strokes
            self.undone_erased_stroke_list = (
                self.undone_erased_stroke_list +
                self.stroke_data_stack[self.current_index_stroke_data_stack:]
            )

            self.stroke_data_stack = self.stroke_data_stack[:
                                                            self.current_index_stroke_data_stack]

        self.stroke_data_stack.append(stroke.copy())
        self.current_index_stroke_data_stack += 1

    # check if the given surface is the same as the newest saved drawing in the undomanager surface_stack
    def compare_drawing_surface_to_last(self, surface):
        # Size must match
        if surface.get_size() != self.surface_stack[self.current_index_surface_stack - 1].get_size():
            return False

        # Pixel content must match
        surface_bytes = pygame.image.tobytes(surface, "RGBA")
        previous_surface_bytes = pygame.image.tobytes(
            self.surface_stack[self.current_index_surface_stack - 1], "RGBA")
        if surface_bytes != previous_surface_bytes:
            return False

        return True

    def undo(self, surface):
        if self.current_index_surface_stack > 1:
            self.current_index_surface_stack -= 1
            surface.blit(
                self.surface_stack[self.current_index_surface_stack - 1], (0, 0))
        if self.current_index_stroke_data_stack > 0 and self.last_drawing_action == DRAW:
            self.current_index_stroke_data_stack -= 1

    def redo(self, surface):
        if self.current_index_surface_stack < len(self.surface_stack):
            surface.blit(
                self.surface_stack[self.current_index_surface_stack], (0, 0))
            self.current_index_surface_stack += 1
        if self.current_index_stroke_data_stack < len(self.stroke_data_stack) and self.last_drawing_action == DRAW:
            self.current_index_stroke_data_stack += 1


# class: Camera
class Camera:
    def __init__(
        self, window_width, window_height, drawing_surface_width, drawing_surface_height, menu_height, drawing_surface
    ):
        self.display_surface = pygame.display.get_surface()
        self.window_width = window_width
        self.window_height = window_height
        self.drawing_surface_width = drawing_surface_width
        self.drawing_surface_height = drawing_surface_height
        self.menu_height = menu_height
        self.drawing_surface = drawing_surface
        self.last_zoom_scale = None
        self.cached_scaled_surface = None
        self.drawing_version = 0
        self.cached_drawing_version = -1

        # camera offset
        self.offset = pygame.math.Vector2(0, 0)

        self.zoom_scale = 1
        self.min_zoom = 1
        self.max_zoom = 1.3

    def reset(self):
        self.last_zoom_scale = None
        self.cached_scaled_surface = None
        self.drawing_version = 0
        self.cached_drawing_version = -1

        self.offset = pygame.math.Vector2(0, 0)

        self.zoom_scale = 1

    # handle zoom functionality

    def zoom(self, zoom_amount):
        screen_center = pygame.math.Vector2(
            self.window_width // 2, (self.window_height - self.menu_height) // 2)
        menu_offset = pygame.math.Vector2(0, self.menu_height)

        old_zoom = self.zoom_scale
        self.zoom_scale = max(self.min_zoom, min(
            self.zoom_scale + zoom_amount, self.max_zoom))

        old_center = (screen_center + self.offset *
                      old_zoom - menu_offset) / old_zoom
        self.offset = old_center - \
            (screen_center - menu_offset) / self.zoom_scale
        self.last_zoom_scale = None

    def zoom_in(self):
        self.zoom(0.1)

    def zoom_out(self):
        self.zoom(-0.1)

    # limit zoom
    def limit_offset(self):
        max_x = self.drawing_surface_width - \
            (self.window_width / self.zoom_scale)
        max_y = self.drawing_surface_height - \
            ((self.window_height - self.menu_height) / self.zoom_scale)

        self.offset.x = max(0, min(self.offset.x, max_x))
        self.offset.y = max(0, min(self.offset.y, max_y))

    def update_scaled_surface(self):
        if self.zoom_scale == 1:
            self.cached_scaled_surface = self.drawing_surface
        else:
            self.cached_scaled_surface = pygame.transform.smoothscale(
                self.drawing_surface,
                (int(self.drawing_surface_width * self.zoom_scale),
                 int(self.drawing_surface_height * self.zoom_scale)),
            )
        self.last_zoom_scale = self.zoom_scale
        self.cached_drawing_version = self.drawing_version

    # display scaled drawing surface with offset
    def custom_display(self):
        if (
            self.zoom_scale != self.last_zoom_scale
            or self.cached_scaled_surface is None
            or self.cached_drawing_version != self.drawing_version
        ):
            self.update_scaled_surface()

        scaled_offset = self.offset * self.zoom_scale
        drawing_surface_offset = pygame.math.Vector2(
            0, self.menu_height) - scaled_offset

        self.display_surface.blit(
            self.cached_scaled_surface, drawing_surface_offset)


# Class: Save Manager: manage saving the drawing of user with their name and time of saving
# Also saves the data related to the drawing self-disclosure width
class SaveManager:
    def __init__(self, surface, child_session_folder_path_publisher):
        self.surface = surface
        self.drawing_surface_width = self.surface.get_width()
        self.drawing_surface_height = self.surface.get_height()
        self.child_session_folder_path_publisher = child_session_folder_path_publisher
        self.session_path = None
        self.drawing_path = None
        self.session_number = None

    def create_saving_folder(self, child_name):
        share_dir = get_package_share_directory("pixelbot_tablet")
        src_dir = share_dir.replace("/install/", "/src/").split("/share/")[0]
        child_folder_path = src_dir + "/saved_drawings/" + child_name
        os.makedirs(child_folder_path, exist_ok=True)

        self.session_number = len(os.listdir(child_folder_path))
        self.session_path = os.path.join(
            child_folder_path, f"session_{self.session_number}")
        os.makedirs(self.session_path, exist_ok=True)

        self.drawing_path = os.path.join(self.session_path, "drawings")
        os.makedirs(self.drawing_path, exist_ok=True)

        child_session_folder_path_msg = String()
        child_session_folder_path_msg.data = self.session_path
        self.child_session_folder_path_publisher.publish(
            child_session_folder_path_msg)

    # save drawing in corresponding child folder and add saving time
    def save_drawing(self, round_id):
        copy_surface = self.surface.copy()

        date = datetime.now().strftime("%d-%m-%Y")
        # timestamp = round(time.time() - activity_start_time, 1)
        drawing_save_path = os.path.join(self.drawing_path, f"{round_id}.png")
        pygame.image.save(copy_surface, drawing_save_path)

    def save_stroke_data_romain(
        self, stroke_data_array, undone_erased_stroke_data_array, activity_time, net_erased_pixels
    ):
        data = {
            "activity_time": activity_time,
            "net_erased_pixels": net_erased_pixels,
            "strokes": stroke_data_array,
            "undone_erased_strokes": undone_erased_stroke_data_array,
        }

        with open(self.session_path + "/strokes.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def serialize_stroke_dict(self, stroke_dict):
        serialized = []

        for stroke in stroke_dict:
            points = stroke.get("points", [])
            if not points:
                continue

            x, y = zip(*points)
            point_count = len(points)

            def get_series(key, fill_value):
                values = list(stroke.get(key, []))
                if len(values) < point_count:
                    values.extend([fill_value] * (point_count - len(values)))
                return values[:point_count]

            serialized.append(
                {
                    "x": np.array(x, dtype=int),
                    "y": np.array(y, dtype=int),
                    "pressure": np.array(get_series("pressure_values", np.nan), dtype=float),
                    "tilt_x": np.array(get_series("tilt_x_values", np.nan), dtype=float),
                    "tilt_y": np.array(get_series("tilt_y_values", np.nan), dtype=float),
                    "pen_color": stroke.get("pen_color"),
                    "pen_size": stroke.get("pen_size"),
                    "tool_type": stroke.get("tool_type", "draw"),
                    "timestamps": np.array(get_series("timestamps", np.nan), dtype=float),
                }
            )

        return np.array(serialized, dtype=object)

    def save_stroke_data(
        self,
        round_id,
        active_stroke_dicts,
        undone_stroke_dicts,
        eraser_stroke_dicts,
        mood_start,
        mood_end,
        emotion: Emotions,
        participant_id,
        round_index,
        round_total,
        arousal_first,
        completion_status,
        drawing_duration_seconds,
        net_erased_pixels,
        session_type="adult",
    ):
        # timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        filename = os.path.join(self.session_path, f"{round_id}.npz")

        strokes = self.serialize_stroke_dict(active_stroke_dicts)
        undone_strokes = self.serialize_stroke_dict(undone_stroke_dicts)
        eraser_strokes = self.serialize_stroke_dict(eraser_stroke_dicts)

        if mood_start is None:
            mood_start = (np.nan, np.nan)
        if mood_end is None:
            mood_end = (np.nan, np.nan)

        np.savez(
            filename,
            strokes=strokes,
            undone_strokes=undone_strokes,
            eraser_strokes=eraser_strokes,
            net_erased_pixels=int(net_erased_pixels),
            mood_start=np.array(mood_start, dtype=float),
            mood_end=np.array(mood_end, dtype=float),
            emotion=emotion.value,
            round_id=round_id,
            participant_id=participant_id,
            session_number=self.session_number,
            round_index=round_index,
            round_total=round_total,
            emotion_name=emotion.name,
            session_type=session_type,
            arousal_first=arousal_first,
            completion_status=completion_status,
            drawing_duration_seconds=float(drawing_duration_seconds),
            saved_at=datetime.now().isoformat(timespec="seconds"),
        )

    def save_session_metadata(self, participant_id, baseline_mood, emotions, arousal_first, session_type):
        filename = os.path.join(self.session_path, "session_metadata.json")

        def clean_float(value):
            if value is None:
                return None
            try:
                if np.isnan(value):
                    return None
            except TypeError:
                pass
            return float(value)

        data = {
            "participant_id": participant_id,
            "session_number": self.session_number,
            "session_type": session_type,
            "baseline_mood": {
                "valence": clean_float(baseline_mood[0]),
                "arousal": clean_float(baseline_mood[1]),
            },
            "emotion_order": [emotion.name for emotion in emotions],
            "arousal_first": bool(arousal_first),
            "language": Message.current_lang.value,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


class PopupWindow:
    def __init__(self, screen_surface, font, clock, title=None):
        if title is None:
            title = Message.get("title_popup")

        self.screen_surface = screen_surface
        self.font = font
        self.clock = clock
        self.title = title
        self.width = self.screen_surface.get_width() // 5
        self.height = self.screen_surface.get_height() // 8
        self.input_text = ""
        self.active_input = False
        self.result = None

        # display only popup rectangle
        self.display_rectangle = pygame.Rect(
            (screen_surface.get_width() - self.width) // 2,
            screen_surface.get_height() // 2 + self.width // 6,
            self.width,
            self.height,
        )

        # display yes and no button
        self.button_yes = pygame.Rect(
            self.display_rectangle.x + 10 / 100 * self.display_rectangle.width,
            self.display_rectangle.y + 60 / 100 * self.display_rectangle.height,
            30 / 100 * self.display_rectangle.width,
            27 / 100 * self.display_rectangle.height,
        )

        self.button_no = pygame.Rect(
            self.display_rectangle.x + 60 / 100 * self.display_rectangle.width,
            self.display_rectangle.y + 60 / 100 * self.display_rectangle.height,
            30 / 100 * self.display_rectangle.width,
            27 / 100 * self.display_rectangle.height,
        )

    # display some text

    def draw_text(self, text, position, color=BLACK):
        rendered_text = self.font.render(text, True, color)
        self.screen_surface.blit(rendered_text, position)

    # display popup window with text
    def display_rectangle_on(self, message, color=(220, 220, 220), border_color=BLACK):
        # Draw main rect
        pygame.draw.rect(self.screen_surface, color, self.display_rectangle)

        # Draw main rect border
        pygame.draw.rect(self.screen_surface, border_color,
                         self.display_rectangle, 2)

        self.draw_text(
            self.title,
            (
                self.display_rectangle.x + 5 / 100 * self.display_rectangle.width,
                self.display_rectangle.y + 10 / 100 * self.display_rectangle.height,
            ),
        )

        message_y = self.display_rectangle.y + 32 / 100 * self.display_rectangle.height
        for line_index, line in enumerate(str(message).splitlines()):
            self.draw_text(
                line,
                (
                    self.display_rectangle.x + 5 / 100 * self.display_rectangle.width,
                    message_y + line_index * self.font.get_linesize(),
                ),
            )

    # ask for comfirmation when trying to close the application
    def ask_confirmation(self, message):
        while self.result is None:
            self.clock.tick(20)
            for event in pygame.event.get():
                check_quit(event)
                if event.type == pygame.MOUSEBUTTONUP:
                    if self.button_yes.collidepoint(event.pos):
                        self.result = "yes"
                    elif self.button_no.collidepoint(event.pos):
                        self.result = "no"

            self.display_rectangle_on(message)
            pygame.draw.rect(self.screen_surface, GREEN, self.button_yes)
            pygame.draw.rect(self.screen_surface, RED, self.button_no)
            self.draw_text(
                Message.get("choice_yes"),
                (
                    self.button_yes.x + 32 / 100 * self.button_yes.width,
                    self.button_yes.y + 14 / 100 * self.button_yes.height,
                ),
            )
            self.draw_text(
                Message.get("choice_no"),
                (
                    self.button_no.x + 38 / 100 * self.button_no.width,
                    self.button_no.y + 14 / 100 * self.button_no.height,
                ),
            )
            pygame.display.update()

        return self.result

    # show window to get input from user
    def handle_input(self, message, is_password=False, max_chars=32):
        error_message = None
        input_box = pygame.Rect(
            self.display_rectangle.x + 5 / 100 * self.display_rectangle.width,
            self.display_rectangle.y + 60 / 100 * self.display_rectangle.height,
            90 / 100 * self.display_rectangle.width,
            25 / 100 * self.display_rectangle.height,
        )

        self.input_text = ""
        self.active_input = True
        MAX_CHAR_LIMIT = max_chars

        while self.result is None:
            self.clock.tick(10)
            for event in pygame.event.get():
                check_quit(event)
                if event.type == pygame.KEYDOWN and self.active_input:
                    if event.key == pygame.K_RETURN:
                        if len(self.input_text) == 0:
                            error_message = Message.get(
                                "error_message_empty_name")
                        else:
                            self.result = self.input_text
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_text = self.input_text[:-1]
                    else:
                        if len(self.input_text) < MAX_CHAR_LIMIT:
                            self.input_text += event.unicode

            self.display_rectangle_on(message)
            pygame.draw.rect(self.screen_surface, WHITE, input_box)
            pygame.draw.rect(self.screen_surface, BLACK, input_box, 2)

            display_text = "*" * \
                len(self.input_text) if is_password else self.input_text
            self.draw_text(
                display_text, (input_box.x + 2 / 100 * input_box.width,
                               input_box.y + 25 / 100 * input_box.height)
            )

            if error_message:
                err_surf = pygame.font.SysFont("arial", max(18, int(self.screen_surface.get_height() * 0.03))).render(
                    error_message, True, RED
                )
                self.screen_surface.blit(
                    err_surf,
                    err_surf.get_rect(
                        midtop=(self.screen_surface.get_width() // 2,
                                int(self.screen_surface.get_width() * 0.43))
                    ),
                )

            pygame.display.update()

        return self.result.lower()


class Stroke_Data:
    def __init__(self):
        self.strokes: list[Stroke] = []

    def update_data(self, current_stroke: dict):
        if current_stroke is not None:
            pos: list[tuple[int, int]] = current_stroke["points"]
            x, y = zip(*pos)

            point_count = len(x)

            def get_series(key, fill_value):
                values = list(current_stroke.get(key, []))
                if len(values) < point_count:
                    values.extend([fill_value] * (point_count - len(values)))
                return values[:point_count]

            pressure = get_series("pressure_values", np.nan)
            tilt_x = get_series("tilt_x_values", np.nan)
            tilt_y = get_series("tilt_y_values", np.nan)
            pen_color = current_stroke.get("pen_color")
            pen_size = current_stroke.get("pen_size")
            timestamps = current_stroke.get("timestamps", [])

            stroke = Stroke(
                x,
                y,
                pressure,
                pen_color=pen_color,
                pen_size=pen_size,
                timestamps=timestamps,
                tilt_x=tilt_x,
                tilt_y=tilt_y,
            )
            self.strokes.append(stroke)

    # This is just a demonstration; the actual analysis should be implemented an an independent module
    # def _analyze_strokes(self, screen, clock):
    #     if not self.strokes:
    #         return ""
    #     stroke = self.strokes[-1]
    #     ana = analyze_strokes(stroke)[1]
    #     # popup = PopupWindow(screen, pygame.font.SysFont('arial', 25), clock)

    #     # popup.ask_confirmation(ana)


class Slider:
    def __init__(
        self,
        center_x,
        center_y,
        track_path,
        thumb_path,
        emoji_left_path,
        emoji_right_path,
        intensity_path,
        min_val=-1.0,
        max_val=1.0,
        initial_val=0.0,
    ):
        self.min_val = min_val
        self.max_val = max_val

        self.track_img, self.track_w, self.track_h = self.load_and_scale(
            track_path)
        self.thumb_img, self.thumb_w, self.thumb_h = self.load_and_scale(
            thumb_path)
        self.emoji_left_img, emoji_w, _ = self.load_and_scale(emoji_left_path)
        self.emoji_right_img, _, _ = self.load_and_scale(emoji_right_path)
        self.intensity_img, intensity_w, intensity_h = self.load_and_scale(
            intensity_path)

        # center on track instead of total area
        center_y -= intensity_h // 2

        self.track_x = center_x - self.track_w // 2
        self.track_y = center_y - self.track_h // 2
        # knob_x calculated dynamically
        # the knob is slightly larger than the track
        self.knob_y = self.track_y - (self.thumb_h - self.track_h) // 2

        self.emoji_y = self.track_y
        # the padding is part of the image -> emojis have same y as track & are directly to the left and right of it
        self.emoji_l_x = self.track_x - emoji_w
        self.emoji_r_x = self.track_x + self.track_w
        self.intensity_x = center_x - intensity_w // 2
        # intensity scale directly below the track
        self.intensity_y = self.track_y + self.thumb_h

        self.knob_min_x = self.track_x
        self.knob_max_x = self.track_x + self.track_w - self.thumb_w

        self._dragging = False
        self.value = np.clip(initial_val, a_min=min_val, a_max=max_val)
        self.knob_x = self._value_to_knob_x(self.value)
        self.touched = False

    def load_and_scale(self, filename, scale=2):
        img = pygame.image.load(filename).convert_alpha()
        w = img.get_width() * scale
        h = img.get_height() * scale
        # scaled_img = pygame.transform.smoothscale(img, (w, h))
        scaled_img = pygame.transform.scale2x(img)
        return scaled_img, w, h

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._track_rect().collidepoint(event.pos):
                self._dragging = True
                self._update_position(event.pos[0])

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self._dragging:  # mouse not on slider anymore but still dragging thumb
                self._update_position(event.pos[0])

    def draw(self, surface):
        surface.blit(self.track_img, (self.track_x, self.track_y))
        surface.blit(self.thumb_img, (self.knob_x, self.knob_y))
        surface.blit(self.emoji_left_img, (self.emoji_l_x, self.emoji_y))
        surface.blit(self.emoji_right_img, (self.emoji_r_x, self.emoji_y))
        surface.blit(self.intensity_img, (self.intensity_x, self.intensity_y))

    def _track_rect(self):
        track_y = self.track_y + (self.thumb_h - self.track_h) // 2
        return pygame.Rect(self.track_x, track_y, self.track_w, self.track_h)

    def _update_position(self, mouse_x):
        mouse_x -= self.thumb_w // 2
        self.knob_x = max(self.knob_min_x, min(self.knob_max_x, mouse_x))
        self._value = self._knob_x_to_value(self.knob_x)
        self.touched = True

    def _knob_x_to_value(self, knob_x):
        t = (knob_x - self.knob_min_x) / (self.knob_max_x - self.knob_min_x)
        self.value = self.min_val + t * \
            (self.max_val - self.min_val)  # this is just a lerp

    def _value_to_knob_x(self, v):
        t = (v - self.min_val) / (self.max_val - self.min_val)
        return self.knob_min_x + t * (self.knob_max_x - self.knob_min_x)


class TextButton:
    # Simple rectangular button with centered text
    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        font: pygame.font.Font,
        bg_color=(230, 230, 230),
        border_color=BLACK,
        text_color=BLACK,
    ):
        self.rect = rect
        self.text = text
        self.font = font
        self.bg_color = bg_color
        self.border_color = border_color
        self.text_color = text_color

    def draw(self, surface: pygame.Surface, hover: bool = False):
        pygame.draw.rect(
            surface, self.bg_color, self.rect, border_radius=int(
                min(self.rect.height, self.rect.width) / 6)
        )
        pygame.draw.rect(
            surface,
            BLUE if hover else self.border_color,
            self.rect,
            width=2,
            border_radius=int(min(self.rect.height, self.rect.width) / 6),
        )
        txt = self.font.render(self.text, True, self.text_color)
        surface.blit(txt, txt.get_rect(center=self.rect.center))

    def is_clicked(self, mouse_pos) -> bool:
        return self.rect.collidepoint(mouse_pos)


####################################################################################################################################################################################################################


class DrawingApplicationNode(Node):

    def __init__(self):
        super().__init__("drawing_application_node")
        pygame.init()

        self.cv_bridge = CvBridge()
        self.drawing_publisher = self.create_publisher(Image, "drawings", 10)

        self.activity_started = False

        self.child_session_folder_path_publisher = self.create_publisher(
            String, "child_session_folder_path", 10)

        self.recognizer_state_publisher = self.create_publisher(
            Bool, "recognizer_is_active", 10)

        # Publisher to display robot processing state
        self.display_robot_state_publisher = self.create_publisher(
            String, "display_robot_state", 10)

        # Publisher of the greeting message, to be said by the sarai tts node
        self.greeting_message_publisher = self.create_publisher(
            String, "tts_input", 10)

        # Publisher to let the other nodes to reset variables when a new draw my life session is started
        self.reset_publisher = self.create_publisher(
            Empty, "reset_drawing_session", 10)

        self.tts_cancel_publisher = self.create_publisher(
            Empty, "tts_cancel", 10)

        # Parameter for pen pressure recording
        if DISABLE_PRESSURE:
            self.declare_parameter("pressure_recording", "disabled")
        else:
            self.declare_parameter("pressure_recording", "enabled")
        self.pressure_recording = self.get_parameter(
            "pressure_recording").get_parameter_value().string_value

        if self.pressure_recording == "enabled":
            self.pressure_reader = WacomPressureReader(require_tilt=True)

            if not self.pressure_reader.wait_until_connected(timeout_s=5.0):
                print(
                    "Error: No suitable Wacom Pen device with pressure and tilt detected!")
                print("Expected: ABS_PRESSURE, ABS_TILT_X, ABS_TILT_Y.")
                exit_program()

            self.last_pressure_warning_time = 0.0

        self.activity_start_time = None

        # Variables for logging the amount of pixel removing done by the user
        self.net_erased_pixels = 0

        # Variables to store the drawing self-disclosure width analysis
        self.current_stroke = None

        if self.pressure_recording == "enabled":
            self.main_screen = pygame.display.set_mode(
                (0, 0), pygame.NOFRAME, display=2)
        else:
            # gets the screen with the lowest ID (should be the tablet)
            last_screen_id = pygame.display.get_num_displays() - 1
            self.main_screen = pygame.display.set_mode(
                (0, 0), pygame.NOFRAME, display=last_screen_id)
        pygame.display.set_caption("drawing interface")
        self.main_screen.fill(WHITE)

        # Defines
        self.WINDOW_WIDTH, self.WINDOW_HEIGHT = self.main_screen.get_size()
        self.GENERAL_ICON_SIZE = (
            2.5 / 100 * self.WINDOW_WIDTH, 2.5 / 100 * self.WINDOW_WIDTH)
        self.MENU_HEIGHT = 10 / 100 * self.WINDOW_HEIGHT
        self.DRAWING_SURFACE_WIDTH, self.DRAWING_SURFACE_HEIGHT = (
            self.WINDOW_WIDTH,
            self.WINDOW_HEIGHT - self.MENU_HEIGHT,
        )

        # different class instances needed for general functionalities
        self.drawing_surface = pygame.Surface(
            (self.DRAWING_SURFACE_WIDTH, self.DRAWING_SURFACE_HEIGHT))

        self.undo_manager = UndoManager()
        self.save_manager = SaveManager(
            self.drawing_surface, self.child_session_folder_path_publisher)
        self.camera = Camera(
            self.WINDOW_WIDTH,
            self.WINDOW_HEIGHT,
            self.DRAWING_SURFACE_WIDTH,
            self.DRAWING_SURFACE_HEIGHT,
            self.MENU_HEIGHT,
            self.drawing_surface,
        )

        self.pencil = Tool(self.camera, self.main_screen,
                           BLACK, 5, self.MENU_HEIGHT)
        self.eraser = Tool(self.camera, self.main_screen,
                           WHITE, 40, self.MENU_HEIGHT)
        self.move_tool = Tool(self.camera, self.main_screen,
                              WHITE, 2, self.MENU_HEIGHT)
        self.active_tool = self.pencil

        # icon positions
        self.pencil_icon_position = (
            1.5 / 100 * self.WINDOW_WIDTH,
            self.MENU_HEIGHT / 2 - self.GENERAL_ICON_SIZE[0] / 2,
        )
        self.eraser_icon_position = (
            4.5 / 100 * self.WINDOW_WIDTH,
            self.MENU_HEIGHT / 2 - self.GENERAL_ICON_SIZE[0] / 2,
        )
        self.move_tool_icon_position = (
            7.5 / 100 * self.WINDOW_WIDTH,
            self.MENU_HEIGHT / 2 - self.GENERAL_ICON_SIZE[0] / 2,
        )
        self.color_icon_position = (
            10.5 / 100 * self.WINDOW_WIDTH,
            self.MENU_HEIGHT / 2 - self.GENERAL_ICON_SIZE[0] / 2,
        )
        self.pencil_size_icon_position = (
            13.5 / 100 * self.WINDOW_WIDTH,
            self.MENU_HEIGHT / 2 - self.GENERAL_ICON_SIZE[0] / 2,
        )
        self.zoom_in_icon_position = (
            16.5 / 100 * self.WINDOW_WIDTH,
            self.MENU_HEIGHT / 2 - self.GENERAL_ICON_SIZE[0] / 2,
        )
        self.zoom_out_icon_position = (
            19.5 / 100 * self.WINDOW_WIDTH,
            self.MENU_HEIGHT / 2 - self.GENERAL_ICON_SIZE[0] / 2,
        )
        self.undo_icon_position = (
            22.5 / 100 * self.WINDOW_WIDTH, self.MENU_HEIGHT / 2 - self.GENERAL_ICON_SIZE[0] / 2)
        self.redo_icon_position = (
            25.5 / 100 * self.WINDOW_WIDTH, self.MENU_HEIGHT / 2 - self.GENERAL_ICON_SIZE[0] / 2)
        self.save_icon_position = (
            self.WINDOW_WIDTH - 3.5 / 100 * self.WINDOW_WIDTH,
            self.MENU_HEIGHT / 2 - self.GENERAL_ICON_SIZE[0] / 2,
        )
        self.documentation_icon_position = (
            self.WINDOW_WIDTH - 6.5 / 100 * self.WINDOW_WIDTH,
            self.MENU_HEIGHT / 2 - self.GENERAL_ICON_SIZE[0] / 2,
        )

        # RGB values for the color palette and the position of the colors
        self.color_palette = [
            # first row
            ((102, 0, 0), (32 / 100 * self.WINDOW_WIDTH,
             0.5 / 100 * self.WINDOW_HEIGHT)),  # dark red
            ((102, 51, 0), (33.75 / 100 * self.WINDOW_WIDTH, 0.5 /
             100 * self.WINDOW_HEIGHT)),  # dark orange / brown
            ((102, 102, 0), (35.5 / 100 * self.WINDOW_WIDTH,
             0.5 / 100 * self.WINDOW_HEIGHT)),  # olive
            ((51, 102, 0), (37.25 / 100 * self.WINDOW_WIDTH,
             0.5 / 100 * self.WINDOW_HEIGHT)),  # dark lime green
            ((0, 102, 0), (39 / 100 * self.WINDOW_WIDTH,
             0.5 / 100 * self.WINDOW_HEIGHT)),  # dark green
            ((0, 102, 51), (40.75 / 100 * self.WINDOW_WIDTH,
             0.5 / 100 * self.WINDOW_HEIGHT)),  # teal green
            ((0, 102, 102), (42.5 / 100 * self.WINDOW_WIDTH,
             0.5 / 100 * self.WINDOW_HEIGHT)),  # teal
            ((0, 51, 102), (44.25 / 100 * self.WINDOW_WIDTH,
             0.5 / 100 * self.WINDOW_HEIGHT)),  # dark sky blue
            ((0, 0, 102), (46 / 100 * self.WINDOW_WIDTH,
             0.5 / 100 * self.WINDOW_HEIGHT)),  # dark blue
            ((51, 0, 102), (47.75 / 100 * self.WINDOW_WIDTH,
             0.5 / 100 * self.WINDOW_HEIGHT)),  # dark violet
            ((102, 0, 102), (49.5 / 100 * self.WINDOW_WIDTH,
             0.5 / 100 * self.WINDOW_HEIGHT)),  # dark magenta
            ((102, 0, 51), (51.25 / 100 * self.WINDOW_WIDTH, 0.5 /
             100 * self.WINDOW_HEIGHT)),  # dark pinkish magenta
            ((32, 32, 32), (53 / 100 * self.WINDOW_WIDTH,
             0.5 / 100 * self.WINDOW_HEIGHT)),  # very dark gray
            ((0, 0, 0), (54.75 / 100 * self.WINDOW_WIDTH,
             0.5 / 100 * self.WINDOW_HEIGHT)),  # black
            # second row
            ((255, 0, 0), (32 / 100 * self.WINDOW_WIDTH,
             3.75 / 100 * self.WINDOW_HEIGHT)),  # pure red
            ((255, 128, 0), (33.75 / 100 * self.WINDOW_WIDTH,
             3.75 / 100 * self.WINDOW_HEIGHT)),  # orange
            ((255, 255, 0), (35.5 / 100 * self.WINDOW_WIDTH,
             3.75 / 100 * self.WINDOW_HEIGHT)),  # yellow
            ((128, 255, 0), (37.25 / 100 * self.WINDOW_WIDTH,
             3.75 / 100 * self.WINDOW_HEIGHT)),  # lime green
            ((0, 255, 0), (39 / 100 * self.WINDOW_WIDTH,
             3.75 / 100 * self.WINDOW_HEIGHT)),  # green
            ((0, 255, 128), (40.75 / 100 * self.WINDOW_WIDTH, 3.75 /
             100 * self.WINDOW_HEIGHT)),  # light greenish-cyan
            ((0, 255, 255), (42.5 / 100 * self.WINDOW_WIDTH,
             3.75 / 100 * self.WINDOW_HEIGHT)),  # cyan (aqua)
            ((0, 128, 255), (44.25 / 100 * self.WINDOW_WIDTH,
             3.75 / 100 * self.WINDOW_HEIGHT)),  # light blue
            ((0, 0, 255), (46 / 100 * self.WINDOW_WIDTH,
             3.75 / 100 * self.WINDOW_HEIGHT)),  # blue
            ((127, 0, 255), (47.75 / 100 * self.WINDOW_WIDTH,
             3.75 / 100 * self.WINDOW_HEIGHT)),  # violet
            ((255, 0, 255), (49.5 / 100 * self.WINDOW_WIDTH,
             3.75 / 100 * self.WINDOW_HEIGHT)),  # magenta (fuchsia)
            ((255, 0, 127), (51.25 / 100 * self.WINDOW_WIDTH,
             3.75 / 100 * self.WINDOW_HEIGHT)),  # pinkish magenta
            ((128, 128, 128), (53 / 100 * self.WINDOW_WIDTH,
             3.75 / 100 * self.WINDOW_HEIGHT)),  # medium gray
            # third row
            ((255, 153, 153), (32 / 100 * self.WINDOW_WIDTH, 7 /
             100 * self.WINDOW_HEIGHT)),  # light red / salmon
            ((255, 204, 153), (33.75 / 100 * self.WINDOW_WIDTH,
             7 / 100 * self.WINDOW_HEIGHT)),  # peach
            ((255, 255, 153), (35.5 / 100 * self.WINDOW_WIDTH,
             7 / 100 * self.WINDOW_HEIGHT)),  # light yellow
            ((204, 255, 153), (37.25 / 100 * self.WINDOW_WIDTH,
             7 / 100 * self.WINDOW_HEIGHT)),  # light lime green
            ((153, 255, 153), (39 / 100 * self.WINDOW_WIDTH,
             7 / 100 * self.WINDOW_HEIGHT)),  # light green
            ((153, 255, 204), (40.75 / 100 * self.WINDOW_WIDTH,
             7 / 100 * self.WINDOW_HEIGHT)),  # light aquamarine
            ((153, 255, 255), (42.5 / 100 * self.WINDOW_WIDTH,
             7 / 100 * self.WINDOW_HEIGHT)),  # light cyan
            ((153, 204, 255), (44.25 / 100 * self.WINDOW_WIDTH,
             7 / 100 * self.WINDOW_HEIGHT)),  # light sky blue
            ((153, 153, 255), (46 / 100 * self.WINDOW_WIDTH,
             7 / 100 * self.WINDOW_HEIGHT)),  # light blue-violet
            ((204, 153, 255), (47.75 / 100 * self.WINDOW_WIDTH,
             7 / 100 * self.WINDOW_HEIGHT)),  # light purple
            ((255, 153, 255), (49.5 / 100 * self.WINDOW_WIDTH,
             7 / 100 * self.WINDOW_HEIGHT)),  # light magenta
            ((255, 153, 204), (51.25 / 100 * self.WINDOW_WIDTH,
             7 / 100 * self.WINDOW_HEIGHT)),  # light pink
            ((204, 204, 204), (53 / 100 * self.WINDOW_WIDTH,
             7 / 100 * self.WINDOW_HEIGHT)),  # light gray
        ]

        # sizes for the pencil and the position of the icons
        self.pencil_size_palette = [
            (2, (32 / 100 * self.WINDOW_WIDTH, self.MENU_HEIGHT /
             2 - self.GENERAL_ICON_SIZE[0] / 2)),
            (5, (35 / 100 * self.WINDOW_WIDTH, self.MENU_HEIGHT /
             2 - self.GENERAL_ICON_SIZE[0] / 2)),
            (10, (38 / 100 * self.WINDOW_WIDTH, self.MENU_HEIGHT /
             2 - self.GENERAL_ICON_SIZE[0] / 2)),
            (15, (41 / 100 * self.WINDOW_WIDTH, self.MENU_HEIGHT /
             2 - self.GENERAL_ICON_SIZE[0] / 2)),
            (25, (44 / 100 * self.WINDOW_WIDTH, self.MENU_HEIGHT /
             2 - self.GENERAL_ICON_SIZE[0] / 2)),
        ]

        # create icon surface from import
        self.pencil_icon_surface = self.load_scale_icon_image(
            "Pencil Image.png")
        self.eraser_icon_surface = self.load_scale_icon_image(
            "Eraser Image.png")
        self.color_icon_surface = self.load_scale_icon_image(
            "Colors Image.png")
        self.pencil_size_icon_surface = self.load_scale_icon_image(
            "Pencil Size Image.png")
        self.undo_icon_surface = self.load_scale_icon_image("Undo Image.png")
        self.redo_icon_surface = self.load_scale_icon_image("Redo Image.png")
        self.undo_icon_gray_surface = self.load_scale_icon_image(
            "Undo Image GRAY.png")
        self.redo_icon_gray_surface = self.load_scale_icon_image(
            "Redo Image GRAY.png")
        self.zoom_in_surface = self.load_scale_icon_image("Zoom In Image.png")
        self.zoom_out_surface = self.load_scale_icon_image(
            "Zoom Out Image.png")
        self.zoom_in_gray_surface = self.load_scale_icon_image(
            "Zoom In Image Gray.png")
        self.zoom_out_gray_surface = self.load_scale_icon_image(
            "Zoom Out Image Gray.png")
        self.move_tool_surface = self.load_scale_icon_image(
            "Move Tool Image.png")
        self.save_icon_surface = self.load_scale_icon_image(
            "Save and Startscreen Image.png")
        self.documentation_icon_surface = self.load_scale_icon_image(
            "Documentation Icon Image.png")

        self.size_xs_surface = self.load_scale_icon_image("Size XS Image.png")
        self.size_s_surface = self.load_scale_icon_image("Size S Image.png")
        self.size_m_surface = self.load_scale_icon_image("Size M Image.png")
        self.size_l_surface = self.load_scale_icon_image("Size L Image.png")
        self.size_xl_surface = self.load_scale_icon_image("Size XL Image.png")

        # background image for small break
        self.break_background_image = pygame.transform.smoothscale(
            pygame.image.load(os.path.join("src", "pixelbot_tablet",
                                           "images", "Small Break Background Image.png")).convert_alpha(), (self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
        self.endscreen_image = pygame.transform.smoothscale(
            pygame.image.load(os.path.join("src", "pixelbot_tablet",
                                           "images", "Endscreen Image.png")).convert_alpha(), (self.WINDOW_WIDTH, self.WINDOW_HEIGHT))

        self.pencil_size_list = [
            self.size_xs_surface,
            self.size_s_surface,
            self.size_m_surface,
            self.size_l_surface,
            self.size_xl_surface,
        ]

        # create Palette class objects
        self.color_palette_instance = Palette(
            self.main_screen, self.color_palette, "color", self.pencil, self.WINDOW_WIDTH
        )
        self.pencil_size_palette_instance = Palette(
            self.main_screen, self.pencil_size_palette, "size", self.pencil, self.WINDOW_WIDTH, self.pencil_size_list
        )

        # create tool rectangles
        self.pencil_icon_rect = self.pencil_icon_surface.get_rect(
            topleft=self.pencil_icon_position)
        self.eraser_icon_rect = self.eraser_icon_surface.get_rect(
            topleft=self.eraser_icon_position)
        self.move_tool_rect = self.move_tool_surface.get_rect(
            topleft=self.move_tool_icon_position)

        # create buttons
        self.color_button = IconButton(
            self.undo_manager,
            self.camera,
            self.color_icon_surface,
            self.color_icon_position,
            self.color_palette_instance,
        )
        self.pencil_size_button = IconButton(
            self.undo_manager,
            self.camera,
            self.pencil_size_icon_surface,
            self.pencil_size_icon_position,
            self.pencil_size_palette_instance,
        )
        self.undo_icon_button = IconButton(
            self.undo_manager,
            self.camera,
            self.undo_icon_surface,
            self.undo_icon_position,
            image_surface_disabled=self.undo_icon_gray_surface,
            type="undo",
        )
        self.redo_icon_button = IconButton(
            self.undo_manager,
            self.camera,
            self.redo_icon_surface,
            self.redo_icon_position,
            image_surface_disabled=self.redo_icon_gray_surface,
            type="redo",
        )
        self.zoom_in_button = IconButton(
            self.undo_manager,
            self.camera,
            self.zoom_in_surface,
            self.zoom_in_icon_position,
            image_surface_disabled=self.zoom_in_gray_surface,
            type="zoom in",
        )
        self.zoom_out_button = IconButton(
            self.undo_manager,
            self.camera,
            self.zoom_out_surface,
            self.zoom_out_icon_position,
            image_surface_disabled=self.zoom_out_gray_surface,
            type="zoom out",
        )
        self.move_tool_button = IconButton(
            self.undo_manager, self.camera, self.move_tool_surface, self.move_tool_icon_position
        )
        self.save_icon_button = IconButton(
            self.undo_manager, self.camera, self.save_icon_surface, self.save_icon_position
        )
        self.documentation_button = IconButton(
            self.undo_manager, self.camera, self.documentation_icon_surface, self.documentation_icon_position
        )

        # create clock object
        self.clock = pygame.time.Clock()
        self.popup_clock = pygame.time.Clock()

        # create Startscreen
        self.start_screen = StartScreenDocumentation(
            self.main_screen,
            os.path.join("src", "pixelbot_tablet",
                         "images", "Welcome Image2.png"),
            os.path.join("src", "pixelbot_tablet",
                         "images", "Start Image.png"),
            os.path.join("src", "pixelbot_tablet",
                         "images", "Exit Button Image.png"),
            os.path.join("src", "pixelbot_tablet",
                         "images", "germany_flag.png"),
            os.path.join("src", "pixelbot_tablet", "images", "uk_flag.png"),
            os.path.join("src", "pixelbot_tablet",
                         "images", "Background Images.png"),
            self.WINDOW_HEIGHT,
            self.WINDOW_WIDTH,
            self.popup_clock,
            self.undo_manager,
            self.camera,
            self.save_manager,
            self.greeting_message_publisher,
        )

        # setup stroke data storage
        self.stroke_data = Stroke_Data()

        self.eraser_strokes = []

        # self.pressure_provider = PressureProvider(
        #     "/dev/input/event6")  # try find device dynamicaly
        # self.pressure_provider.start()

        self.quit = False
        self.mood_induction_duration = 3 * 60
        self.drawing_duration = 5 * 60

        self.current_round_id = None
        self.session_type = SessionType.Adult
        self.selected_emotions = [Emotions.EXCITEMENT,
                                  Emotions.ANGER, Emotions.SADNESS]
        self.arousal_first = False

        # start drawing app
        self.run_main_loop()

    # load image from filename and scale it
    def load_scale_icon_image(self, filename):
        file_path = os.path.join("src", "pixelbot_tablet", "images", filename)
        return pygame.transform.smoothscale(pygame.image.load(file_path).convert_alpha(), self.GENERAL_ICON_SIZE)

    def make_round_id(self, emotion: Emotions) -> str:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"session{self.save_manager.session_number}_{emotion.name.lower()}_{stamp}"

    # reset attributes for new child to start new drawing session
    def reset(self):
        self.undo_manager.reset()
        self.stroke_data = Stroke_Data()
        self.eraser_strokes = []
        self.active_tool = self.pencil
        self.pencil.active = False
        self.pencil.last_position = None
        self.pencil.last_add_point_time = None
        self.eraser.active = False
        self.eraser.last_position = None
        self.eraser.last_add_point_time = None
        self.move_tool.active = False
        self.move_tool.last_position = None
        self.move_tool.last_add_point_time = None
        self.pencil.color = BLACK
        self.pencil.tool_size = 5
        self.camera.reset()
        self.current_stroke = None
        self.activity_started = False
        self.net_erased_pixels = 0
        self.color_palette_instance.hide()
        self.pencil_size_palette_instance.hide()

        Message.current_lang = Language.English
        self.start_screen.germany_button.active = False
        self.start_screen.english_button.active = True

        publish_tts_cancel(self.tts_cancel_publisher)

        # Reset of the variables in the other nodes
        reset_msg = Empty()
        self.reset_publisher.publish(reset_msg)

    def send_drawing_to_vlm(self):
        if self.activity_started:
            # save drawing surface as opencv image
            display_surface = self.drawing_surface.copy()

            # Scale the image down to decrease the vlm processing time
            display_surface_size = display_surface.get_size()
            scaled_down_size = tuple(s / 4 for s in display_surface_size)
            scaled_down_display_surface = pygame.transform.scale(
                display_surface, scaled_down_size)

            img_array = np.array(pygame.surfarray.array3d(
                scaled_down_display_surface))

            image_object = np.transpose(img_array, (1, 0, 2))
            image_object = cv2.cvtColor(image_object, cv2.COLOR_RGB2BGR)

            # publish images
            ros_image = self.cv_bridge.cv2_to_imgmsg(image_object)
            self.drawing_publisher.publish(ros_image)

    def reset_drawing_phase(self):
        self.undo_manager.reset()
        self.stroke_data = Stroke_Data()
        self.eraser_strokes = []
        self.active_tool = self.pencil
        self.current_stroke = None
        self.net_erased_pixels = 0

        for tool in (self.pencil, self.eraser, self.move_tool):
            tool.active = False
            tool.last_position = None
            tool.last_add_point_time = None
            tool.button_down_time = None
            tool.ink_pixel_before_erased = None

        self.pencil.color = BLACK
        self.pencil.tool_size = 5
        self.camera.reset()
        self.color_palette_instance.hide()
        self.pencil_size_palette_instance.hide()
        self.drawing_surface.fill(WHITE)
        self.undo_manager.append_drawing(self.drawing_surface)
        self.camera.drawing_version += 1

    def finalize_drawing_input(self):
        if self.active_tool == self.eraser and self.eraser.active and self.eraser.ink_pixel_before_erased is not None:
            ink_after_erased = count_ink_pixels(self.drawing_surface)
            self.net_erased_pixels += self.eraser.ink_pixel_before_erased - ink_after_erased
            self.undo_manager.last_drawing_action = ERASE

        if self.current_stroke:
            tool_type = self.current_stroke.get("tool_type", "draw")

            if tool_type == "draw":
                self.undo_manager.append_stroke(self.current_stroke)
                self.stroke_data.update_data(self.current_stroke)
                self.undo_manager.last_drawing_action = DRAW
            elif tool_type == "erase":
                self.eraser_strokes.append(self.current_stroke.copy())
                self.undo_manager.last_drawing_action = ERASE

            self.current_stroke = None

        if not self.undo_manager.surface_stack or not self.undo_manager.compare_drawing_surface_to_last(
            self.drawing_surface
        ):
            self.undo_manager.append_drawing(self.drawing_surface)

        for tool in (self.pencil, self.eraser, self.move_tool):
            tool.active = False
            tool.last_position = None

    def format_timer_text(self, remaining_seconds: int) -> str:
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def draw_timer(self, surface, remaining_seconds: int, menu_mode=False):
        timer_font = pygame.font.SysFont(
            "arial", max(18, int(self.WINDOW_HEIGHT * 0.025)))
        timer_surface = timer_font.render(
            self.format_timer_text(remaining_seconds), True, BLACK)

        padding_x = 12
        padding_y = 6
        box = pygame.Rect(0, 0, timer_surface.get_width() + 2 *
                          padding_x, timer_surface.get_height() + 2 * padding_y)

        if menu_mode:
            box.right = self.WINDOW_WIDTH - 200
            box.centery = self.MENU_HEIGHT // 2
        else:
            box.right = self.WINDOW_WIDTH - 24
            box.top = 24

        pygame.draw.rect(surface, WHITE, box, border_radius=10)
        pygame.draw.rect(surface, GRAY, box, width=2, border_radius=10)
        surface.blit(timer_surface, timer_surface.get_rect(center=box.center))

    def wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> list[str]:
        wrapped_lines = []

        for raw_line in text.splitlines():
            words = raw_line.split()
            if not words:
                wrapped_lines.append("")
                continue

            current_line = words[0]

            for word in words[1:]:
                candidate = current_line + " " + word
                if font.size(candidate)[0] <= max_width:
                    current_line = candidate
                else:
                    wrapped_lines.append(current_line)
                    current_line = word

            wrapped_lines.append(current_line)

        return wrapped_lines

    def display_text(self, text: str, font_size=64, sep=24, show_continue=False, show_break_image=False, show_end_image=False):
        lines = text.splitlines()
        n_lines = len(lines)

        font = pygame.font.SysFont("arial", font_size)
        rendered_text = [font.render(line, True, (0, 0, 0)) for line in lines]

        total_height = sum(surface.get_height()
                           for surface in rendered_text) + sep * (n_lines - 1)
        total_width = max(surface.get_width() for surface in rendered_text)

        x_adjust = (self.WINDOW_WIDTH - total_width) // 2
        y_adjust = (self.WINDOW_HEIGHT - total_height) // 2

        if show_continue:
            button_w = int(self.WINDOW_WIDTH * 0.20)
            button_h = int(self.WINDOW_HEIGHT * 0.07)
            button_y = int(self.WINDOW_HEIGHT // 1.3 +
                           self.WINDOW_HEIGHT * 0.08)
            button_y = min(button_y, self.WINDOW_HEIGHT -
                           button_h - int(self.WINDOW_HEIGHT * 0.05))
            size = pygame.Rect(self.WINDOW_WIDTH // 2 -
                               button_w // 2, button_y, button_w, button_h)
            self.continue_button = TextButton(
                size,
                Message.get("button_continue"),
                pygame.font.SysFont("arial", max(
                    22, int(self.WINDOW_HEIGHT * 0.04))),
            )

        running = True
        while running:
            for event in pygame.event.get():
                check_quit(event)
                # don't allow the user to exit this screen; only the instructors should be able to do that
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    publish_tts_cancel(self.tts_cancel_publisher)
                    running = False

                if show_continue and event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if self.continue_button.is_clicked(event.pos):
                        publish_tts_cancel(self.tts_cancel_publisher)
                        return

            self.main_screen.fill(WHITE)
            if show_break_image:
                self.main_screen.blit(self.break_background_image, (0, 0))
            if show_end_image:
                self.main_screen.blit(self.endscreen_image, (0, 0))

            y_in_box = 0.0
            for text_line in rendered_text:
                w = text_line.get_width()
                h = text_line.get_height()

                x_in_box = (total_width - w) // 2
                self.main_screen.blit(
                    text_line, (x_in_box + x_adjust, y_in_box + y_adjust))

                y_in_box += h + sep

            if show_continue:
                hover = self.continue_button.rect.collidepoint(
                    pygame.mouse.get_pos())
                self.continue_button.draw(self.main_screen, hover=hover)
            self.clock.tick(10)
            pygame.display.flip()

    # displays timed text with a continue button to skip the timed text

    def display_timed_text(self, text: str, duration_seconds: int, font_size=64, sep=24, first_lines=None, use_skip_button=False):
        max_text_width = int(self.WINDOW_WIDTH * 0.8)
        font = pygame.font.SysFont("arial", font_size)
        lines = self.wrap_text(text, font, max_text_width)

        if use_skip_button:
            button_w = int(self.WINDOW_WIDTH * 0.1)
            button_h = int(self.WINDOW_HEIGHT * 0.05)
            button_y = int(self.WINDOW_HEIGHT // 1.3 +
                           self.WINDOW_HEIGHT * 0.08)
            button_y = min(button_y, self.WINDOW_HEIGHT -
                           button_h - int(self.WINDOW_HEIGHT * 0.05))
            self.continue_button = TextButton(
                pygame.Rect(self.WINDOW_WIDTH * 7 // 8 - button_w //
                            2, button_y, button_w, button_h),
                Message.get("button_skip"),
                pygame.font.SysFont("arial", 24),
            )
        else:
            button_w = int(self.WINDOW_WIDTH * 0.20)
            button_h = int(self.WINDOW_HEIGHT * 0.07)
            button_y = int(self.WINDOW_HEIGHT // 1.3 +
                           self.WINDOW_HEIGHT * 0.08)
            button_y = min(button_y, self.WINDOW_HEIGHT -
                           button_h - int(self.WINDOW_HEIGHT * 0.05))
            self.continue_button = TextButton(
                pygame.Rect(self.WINDOW_WIDTH // 2 - button_w //
                            2, button_y, button_w, button_h),
                Message.get("button_continue"),
                pygame.font.SysFont("arial", max(
                    22, int(self.WINDOW_HEIGHT * 0.04))),
            )

        if first_lines is not None:
            first_line_p3 = lines[0]
            lines = lines[1:]
            bold_font = pygame.font.SysFont("arial", font_size, bold=True)

        n_lines = len(lines)
        rendered_text = [font.render(line, True, BLACK) for line in lines]

        total_height = sum(surface.get_height()
                           for surface in rendered_text) + sep * (n_lines - 1)
        total_width = max(surface.get_width() for surface in rendered_text)

        if first_lines is not None:
            first_line_p1, mood = first_lines
            lines_first_line = self.wrap_text(
                first_line_p1, font, max_text_width)

            n_normal_lines = len(lines_first_line) - 1
            normal_lines = [font.render(line, True, BLACK)
                            for line in lines_first_line[:-1]]

            extra_lines = [
                font.render(lines_first_line[-1], True, BLACK),
                bold_font.render(mood, True, BLACK),
                font.render(first_line_p3, True, BLACK),
            ]

            bold_spacing = 18
            extra_w = sum(surface.get_width()
                          for surface in extra_lines) + 2 * bold_spacing
            extra_h = max(surface.get_height() for surface in extra_lines)

            rendered_text = rendered_text

            total_height += sum(surface.get_height()
                                for surface in normal_lines) + sep * (n_normal_lines + 1) + extra_h
            total_width = max(
                total_width, extra_w, 0 if not normal_lines else max(
                    surface.get_width() for surface in normal_lines)
            )

        x_adjust = (self.WINDOW_WIDTH - total_width) // 2
        y_adjust = (self.WINDOW_HEIGHT - total_height) // 2

        end_time = time.time() + duration_seconds

        while True:
            self.clock.tick(30)

            for event in pygame.event.get():
                # don't allow the user to exit this screen; only the instructors should be able to do that
                check_quit(event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                    publish_tts_cancel(self.tts_cancel_publisher)
                    self.quit = True
                    return
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    # NOTE: if you move the sliders, and while moving them you put your mouse on the continue button, and then release the mouse, the continue button is activated
                    # We might want to prevent this? or not idk. atleast the slider values seem to be saved correctly...
                    if self.continue_button.is_clicked(event.pos):
                        publish_tts_cancel(self.tts_cancel_publisher)
                        return

            remaining_seconds = max(0, int(end_time - time.time() + 0.999))
            if remaining_seconds == 0:
                publish_tts_cancel(self.tts_cancel_publisher)
                return

            self.main_screen.fill(WHITE)
            y_in_box = 0.0

            if first_lines is not None:
                for text_line in normal_lines:
                    w = text_line.get_width()
                    h = text_line.get_height()

                    x_in_box = (total_width - w) // 2
                    self.main_screen.blit(
                        text_line, (x_in_box + x_adjust, y_in_box + y_adjust))
                    y_in_box += h + sep

                # line with bold item
                w = extra_w
                h = extra_h
                x_in_box = (total_width - w) // 2
                for i, text_line in enumerate(extra_lines):
                    self.main_screen.blit(
                        text_line, (x_in_box + x_adjust, y_in_box + y_adjust))
                    x_in_box += text_line.get_width() + bold_spacing
                    # for some reason, whitespace at the beginning and end are trimmed so we have to do this abomination
                    if i == 1 and Message.current_lang == Language.English:
                        x_in_box -= bold_spacing
                y_in_box += h + sep

            for text_line in rendered_text:
                w = text_line.get_width()
                h = text_line.get_height()

                x_in_box = (total_width - w) // 2
                self.main_screen.blit(
                    text_line, (x_in_box + x_adjust, y_in_box + y_adjust))
                y_in_box += h + sep

            self.draw_timer(self.main_screen, remaining_seconds)
            hover = self.continue_button.rect.collidepoint(
                pygame.mouse.get_pos())
            self.continue_button.draw(self.main_screen, hover=hover)
            pygame.display.flip()

    # start drawing: let user draw by getting user input and display UI
    def run_game(self, duration_seconds=None, disable_timer=False, save_result=True):

        if duration_seconds is None:
            duration_seconds = self.drawing_duration

        if disable_timer:
            # if the timer is disabled, just set it to an extremely high value (136 years)
            duration_seconds = 0xFFFFFFFF

        self.reset_drawing_phase()
        self.activity_start_time = time.time()
        self.activity_started = True
        phase_end_time = self.activity_start_time + duration_seconds

        last_debug_time = time.time()
        last_timer_value = None
        redraw_canvas = True
        redraw_menu = True

        canvas_rect = pygame.Rect(
            0, self.MENU_HEIGHT + 2, self.WINDOW_WIDTH, self.WINDOW_HEIGHT - self.MENU_HEIGHT)
        menu_rect = pygame.Rect(0, 0, self.WINDOW_WIDTH, self.MENU_HEIGHT)

        while True:
            self.clock.tick(30)
            areas_to_update = []

            remaining_seconds = max(
                0, int(phase_end_time - time.time() + 0.999))
            if remaining_seconds != last_timer_value:
                redraw_menu = True
                last_timer_value = remaining_seconds

            # event loop
            event_list = pygame.event.get()
            for event in event_list:

                if event.type == pygame.QUIT:  # react to closing the window / pressing Alt+F4
                    self.finalize_drawing_input()
                    if save_result and self.current_round_id is not None:
                        self.save_manager.save_drawing(self.current_round_id)
                    # self.reset()
                    self.quit = True
                    return "quit"

                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                    if event.pos[1] >= self.MENU_HEIGHT:
                        redraw_canvas = True
                    else:
                        redraw_menu = True

                if event.type == pygame.MOUSEBUTTONDOWN:

                    mouse_position = pygame.mouse.get_pos()

                    # click pencil
                    if self.pencil_icon_rect.collidepoint(mouse_position):
                        self.active_tool = self.pencil

                    # click eraser
                    if self.eraser_icon_rect.collidepoint(mouse_position):
                        self.active_tool = self.eraser

                    # click move tool
                    if self.move_tool_rect.collidepoint(mouse_position):
                        self.active_tool = self.move_tool

                    # click color palette
                    if self.color_button.check_click(mouse_position):
                        self.pencil_size_button.palette.hide()
                        self.color_button.handle_click()

                    # click pencil size palette
                    if self.pencil_size_button.check_click(mouse_position):
                        self.color_button.palette.hide()
                        self.pencil_size_button.handle_click()

                    # click undo button
                    if self.undo_icon_button.check_click(mouse_position):
                        ink_before_undo = count_ink_pixels(
                            self.drawing_surface)

                        self.undo_manager.undo(self.drawing_surface)
                        self.camera.drawing_version += 1

                        ink_after_undo = count_ink_pixels(self.drawing_surface)
                        number_undone_pixels = ink_before_undo - ink_after_undo
                        self.net_erased_pixels += number_undone_pixels

                        redraw_canvas = True

                    # click redo button
                    if self.redo_icon_button.check_click(mouse_position):
                        ink_before_redo = count_ink_pixels(
                            self.drawing_surface)

                        self.undo_manager.redo(self.drawing_surface)
                        self.camera.drawing_version += 1

                        ink_after_redo = count_ink_pixels(self.drawing_surface)
                        number_redone_pixels = ink_before_redo - ink_after_redo
                        self.net_erased_pixels += number_redone_pixels

                        redraw_canvas = True

                    # click zoom in button
                    if self.zoom_in_button.check_click(mouse_position):
                        self.camera.zoom_in()
                        redraw_canvas = True

                    # click zoom out button
                    if self.zoom_out_button.check_click(mouse_position):
                        self.camera.zoom_out()
                        redraw_canvas = True

                    # check what user chooses in palette
                    self.color_palette_instance.handle_palette_click(
                        mouse_position)
                    self.pencil_size_palette_instance.handle_palette_click(
                        mouse_position)

                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:

                    # make undo button black
                    redraw_menu = True

                    # if user drew or erased something: capture current drawing
                    mouse_position = pygame.mouse.get_pos()
                    if (self.active_tool == self.pencil or self.active_tool == self.eraser) and mouse_position[
                        1
                    ] >= self.MENU_HEIGHT:

                        if not self.undo_manager.compare_drawing_surface_to_last(self.drawing_surface):
                            self.undo_manager.append_drawing(
                                self.drawing_surface)

                        # Pencil tool is released: current stroke is finished, save it
                        # Note: A stroke needs to have at least two points
                        # if pencil tool is released, but there were no movements previously
                        # then current_stroke is none because it is only made of one point
                        # so we don't consider that to be a stroke and we don't save anything
                        if self.active_tool == self.pencil and self.current_stroke:
                            self.undo_manager.append_stroke(
                                self.current_stroke)
                            self.stroke_data.update_data(self.current_stroke)

                            self.current_stroke = None
                            self.undo_manager.last_drawing_action = DRAW

                        if self.active_tool == self.eraser and self.current_stroke:
                            self.eraser_strokes.append(
                                self.current_stroke.copy())
                            self.current_stroke = None
                            self.undo_manager.last_drawing_action = ERASE

                    # click save button
                    if self.save_icon_button.check_click(mouse_position):
                        popup = PopupWindow(self.main_screen, pygame.font.SysFont(
                            "arial", 25), self.popup_clock)
                        answer = popup.ask_confirmation(
                            Message.get("msg_save"))
                        if answer == "yes":
                            # activity_time = time.time() - self.activity_start_time

                            # save all data
                            self.finalize_drawing_input()
                            if save_result and self.current_round_id is not None:
                                self.save_manager.save_drawing(
                                    self.current_round_id)
                            # clean_stroke_data_stack = self.undo_manager.stroke_data_stack[:self.undo_manager.current_index_stroke_data_stack]
                            # undone_erased_stroke_data_array = self.undo_manager.undone_erased_stroke_list + self.undo_manager.stroke_data_stack[self.undo_manager.current_index_stroke_data_stack:]
                            # self.save_manager.save_stroke_data(clean_stroke_data_stack, undone_erased_stroke_data_array, activity_time, self.net_erased_pixels)

                            # reset all variables and other nodes
                            # self.reset()

                            return "manual_save"

                    # click documentation button
                    if self.documentation_button.check_click(mouse_position):
                        self.start_screen.show_documentation()
                        redraw_canvas = True
                        redraw_menu = True

                if self.pressure_recording == "enabled":
                    pressure_state = self.pressure_reader.get_state(
                        max_age_s=0.75)

                    is_pen_motion_on_canvas = (
                        event.type == pygame.MOUSEMOTION
                        and self.active_tool in (self.pencil, self.eraser)
                        and self.active_tool.active
                        and event.pos[1] >= self.MENU_HEIGHT
                    )

                    if is_pen_motion_on_canvas and not pressure_state["valid"]:
                        now = time.time()

                        if now - self.last_pressure_warning_time > 1.0:
                            print(
                                "Warning: skipping drawing motion because Wacom pressure/tilt "
                                f"is not valid. connected={pressure_state['connected']}, "
                                f"event_age={pressure_state['event_age']:.3f}, "
                                f"device={pressure_state['device_path']}"
                            )
                            self.last_pressure_warning_time = now

                        # Prevent a long jump line when the signal comes back.
                        self.active_tool.last_position = None
                        continue

                    self.current_stroke, number_erased_pixels = self.active_tool.handle_event(
                        event,
                        self.drawing_surface,
                        self.pencil,
                        self.eraser,
                        self.move_tool,
                        self.active_tool,
                        self.MENU_HEIGHT,
                        self.current_stroke,
                        self.activity_start_time,
                        pressure_state["pressure"],
                        pressure_state["tilt_x"],
                        pressure_state["tilt_y"],
                    )
                    self.net_erased_pixels += number_erased_pixels

                else:
                    self.current_stroke, number_erased_pixels = self.active_tool.handle_event(
                        event,
                        self.drawing_surface,
                        self.pencil,
                        self.eraser,
                        self.move_tool,
                        self.active_tool,
                        self.MENU_HEIGHT,
                        self.current_stroke,
                        self.activity_start_time,
                    )
                    self.net_erased_pixels += number_erased_pixels

            # send last drawing version to vlm node
            if time.time() - last_debug_time >= 5:
                # self.send_drawing_to_vlm()
                last_debug_time = time.time()

            if remaining_seconds == 0:
                self.finalize_drawing_input()
                if save_result and self.current_round_id is not None:
                    self.save_manager.save_drawing(self.current_round_id)
                return "time_expired_save"

            if redraw_canvas:
                # display drawing surface and limit offset
                pygame.draw.rect(self.drawing_surface, BLUE,
                                 self.drawing_surface.get_rect(), BLUE_BORDER_THICKNESS)
                self.camera.limit_offset()
                self.camera.custom_display()

                self.eraser.display_eraser_border(
                    self.active_tool, self.eraser, self.MENU_HEIGHT)

                self.draw_timer(self.main_screen,
                                remaining_seconds, menu_mode=True)

                areas_to_update.append(canvas_rect)
                redraw_canvas = False

            if redraw_menu:

                # display interface components
                pygame.draw.rect(self.main_screen, WHITE, (0, 0,
                                 self.DRAWING_SURFACE_WIDTH, self.MENU_HEIGHT))

                pygame.draw.line(
                    self.main_screen, BLACK, (0, self.MENU_HEIGHT), (
                        self.WINDOW_WIDTH, self.MENU_HEIGHT), 2
                )

                # display tool icons with fitting border
                self.main_screen.blit(
                    self.pencil_icon_surface, self.pencil_icon_rect)
                self.main_screen.blit(
                    self.eraser_icon_surface, self.eraser_icon_rect)
                self.main_screen.blit(
                    self.move_tool_surface, self.move_tool_rect)
                self.pencil.display_borders_tool(
                    self.pencil_icon_rect, self.active_tool)
                self.eraser.display_borders_tool(
                    self.eraser_icon_rect, self.active_tool)

                self.move_tool.display_borders_tool(
                    self.move_tool_rect, self.active_tool)

                # display buttons
                self.color_button.display(self.main_screen, self.pencil.color)
                self.pencil_size_button.display(self.main_screen, GRAY)
                self.undo_icon_button.display(self.main_screen, GRAY)
                self.redo_icon_button.display(self.main_screen, GRAY)
                self.zoom_in_button.display(self.main_screen, GRAY)
                self.zoom_out_button.display(self.main_screen, GRAY)
                self.save_icon_button.display(self.main_screen, GRAY)
                self.documentation_button.display(self.main_screen, GRAY)

                # display palettes
                self.color_palette_instance.display(self.main_screen, GRAY)
                self.pencil_size_palette_instance.display(
                    self.main_screen, GRAY)

                if not disable_timer:
                    self.draw_timer(self.main_screen,
                                    remaining_seconds, menu_mode=True)

                areas_to_update.append(menu_rect)
                redraw_menu = False

            if areas_to_update:
                pygame.display.update(areas_to_update)

    def is_adult_session(self) -> bool:
        return self.session_type == SessionType.Adult

    def small_break(self, round_index: int, rounds_total: int):
        self.display_text(Message.get("msg_small_break"),
                          font_size=48, show_continue=True, show_break_image=True)

    def mood_repair_session(self):
        self.display_text(Message.get("msg_mood_repair_draw_robot"),
                          font_size=44, show_continue=True)
        self.current_round_id = None
        self.run_game(disable_timer=True, save_result=False)

    def run_study(self):
        # Show setup screen (the participants should never see this!)
        keep_continue = self.start_screen.run_setup()
        if not keep_continue:
            self.quit = True
            return

        # self.session_type = self.start_screen.session_type
        # If the language is set to German -> use child version
        self.session_type = SessionType.Adult if Message.current_lang == Language.English else SessionType.Child

        emotions = list(self.start_screen.selected_emotions)

        # positive = random.choice([Emotions.EXCITEMENT, Emotions.CONTENTMENT])
        # negative = random.choice([Emotions.ANGER, Emotions.SADNESS])
        # emotions = [positive, negative, Emotions.NEUTRAL]
        # random.shuffle(emotions)

        self.selected_emotions = emotions
        # Slider order is fixed: valence first, arousal second.
        self.arousal_first = False
        rounds_total = len(emotions)

        # Show start screen (for participants) + documentation
        self.start_screen.run_start()

        # Baseline mood assessment: adults = valence + arousal, children = valence only.
        baseline_mood = self.mood_assessment(
            include_arousal=self.is_adult_session())

        self.current_round_id = None

        # Allow participant to play with the drawing application before the study.
        self.run_game(disable_timer=True, save_result=False)

        greeting_text = Message.get("msg_tts_greeting")
        publish_tts_request(self.greeting_message_publisher,
                            greeting_text, Message.current_lang)

        # Save metadata for whole session.
        self.save_manager.save_session_metadata(
            participant_id=self.start_screen.child_name,
            baseline_mood=baseline_mood,
            emotions=emotions,
            arousal_first=self.arousal_first,
            session_type=self.session_type.value,
        )

        self.display_text(Message.get("msg_start_study"), show_continue=True)

        for round_index, emotion in enumerate(emotions, start=1):
            self.current_round_id = self.make_round_id(emotion)

            # Mood induction.
            self.mood_induction(emotion)

            # Adults: mood assessment before drawing.
            # Children: no mood assessment before drawing.
            if self.is_adult_session():
                mood_start = self.mood_assessment(include_arousal=True)
            else:
                mood_start = (np.nan, np.nan)

            # Drawing activity.
            drawing_start_time = time.time()
            completion_status = self.run_game(self.drawing_duration)
            drawing_duration_seconds = time.time() - drawing_start_time

            # Mood assessment after drawing.
            # Adults: valence + arousal. Children: valence only.
            mood_end = self.mood_assessment(
                include_arousal=self.is_adult_session())

            active_strokes = self.undo_manager.stroke_data_stack[:
                                                                 self.undo_manager.current_index_stroke_data_stack]
            undone_strokes = (
                self.undo_manager.undone_erased_stroke_list
                + self.undo_manager.stroke_data_stack[self.undo_manager.current_index_stroke_data_stack:]
            )

            # Save the round data.
            self.save_manager.save_stroke_data(
                round_id=self.current_round_id,
                active_stroke_dicts=active_strokes,
                undone_stroke_dicts=undone_strokes,
                eraser_stroke_dicts=self.eraser_strokes,
                mood_start=mood_start,
                mood_end=mood_end,
                emotion=emotion,
                participant_id=self.start_screen.child_name,
                round_index=round_index,
                round_total=rounds_total,
                arousal_first=self.arousal_first,
                completion_status=completion_status,
                drawing_duration_seconds=drawing_duration_seconds,
                net_erased_pixels=self.net_erased_pixels,
                session_type=self.session_type.value,
            )

            # Small break after each round, including the third round.
            self.small_break(round_index, rounds_total)

        # Mood repair procedure at the end of the experiment.
        self.mood_repair_session()

        # Displays exit message.
        self.display_text(Message.get("msg_study_end"), show_end_image=True)

    def mood_induction(self, emotion: Emotions):
        if self.is_adult_session():
            neutral_key = "msg_study_mood_induction_neutral"
            sentence_1_key = "msg_study_mood_induction_sentence_1"
            rest_key = "msg_study_mood_induction"
        else:
            neutral_key = "msg_child_mood_induction_neutral"
            sentence_1_key = "msg_child_mood_induction_sentence_1"
            rest_key = "msg_child_mood_induction"

        if emotion is Emotions.NEUTRAL:
            instruction = Message.get(neutral_key)
            publish_tts_request(self.greeting_message_publisher,
                                instruction, Message.current_lang)
            self.display_timed_text(
                instruction, self.mood_induction_duration, font_size=48, use_skip_button=True)
        else:
            mood_map = {
                Emotions.EXCITEMENT: Message.get("mood_excited"),
                Emotions.ANGER: Message.get("mood_angry"),
                Emotions.CONTENTMENT: Message.get("mood_contentment"),
                Emotions.SADNESS: Message.get("mood_sad"),
            }
            mood = mood_map[emotion]
            instruction_s1 = Message.get(sentence_1_key)
            instruction_rest = Message.get(rest_key)
            instruction = instruction_s1 + mood + instruction_rest

            publish_tts_request(self.greeting_message_publisher,
                                instruction, Message.current_lang)

            self.display_timed_text(
                instruction_rest,
                self.mood_induction_duration,
                font_size=48,
                first_lines=[instruction_s1, mood],
                use_skip_button=True,
            )

    def draw_slider_label(self, text: str, center_x: int, top_y: int):
        label_font = pygame.font.SysFont(
            "arial", max(20, int(self.WINDOW_HEIGHT * 0.028)))
        label_surface = label_font.render(text, True, BLACK)
        label_rect = label_surface.get_rect(center=(center_x, top_y))
        self.main_screen.blit(label_surface, label_rect)

    def mood_assessment(self, include_arousal=True) -> tuple[float, float]:
        error_msg = None
        center_x = self.WINDOW_WIDTH // 2

        if include_arousal:
            valence_y = self.WINDOW_HEIGHT // 3
            arousal_y = self.WINDOW_HEIGHT * 2 // 3
        else:
            valence_y = self.WINDOW_HEIGHT // 2
            arousal_y = None

        resource_path = os.path.join(
            "src", "pixelbot_tablet", "images", "slider")
        slider_valence = Slider(
            center_x,
            valence_y,
            os.path.join(resource_path, "AS_track.png"),
            os.path.join(resource_path, "AS_thumb.png"),
            os.path.join(resource_path, "AS_unhappy.png"),
            os.path.join(resource_path, "AS_happy.png"),
            os.path.join(resource_path, "AS_intensity_cue.png"),
        )

        slider_arousal = None
        if include_arousal:
            slider_arousal = Slider(
                center_x,
                arousal_y,
                os.path.join(resource_path, "AS_track.png"),
                os.path.join(resource_path, "AS_thumb.png"),
                os.path.join(resource_path, "AS_sleepy.png"),
                os.path.join(resource_path, "AS_wideawake.png"),
                os.path.join(resource_path, "AS_intensity_cue.png"),
            )

        button_w = int(self.WINDOW_WIDTH * 0.20)
        button_h = int(self.WINDOW_HEIGHT * 0.07)
        button_y = int(self.WINDOW_HEIGHT // 1.3 + self.WINDOW_HEIGHT * 0.08)
        button_y = min(button_y, self.WINDOW_HEIGHT -
                       button_h - int(self.WINDOW_HEIGHT * 0.05))
        self.continue_button = TextButton(
            pygame.Rect(self.WINDOW_WIDTH // 2 - button_w //
                        2, button_y, button_w, button_h),
            Message.get("button_continue"),
            pygame.font.SysFont("arial", max(
                22, int(self.WINDOW_HEIGHT * 0.04))),
        )

        running = True
        while running:
            for event in pygame.event.get():
                check_quit(event)
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if self.continue_button.is_clicked(event.pos):
                        if include_arousal:
                            sliders_touched = slider_valence.touched and slider_arousal.touched
                            error_key = "msg_slider_error"
                        else:
                            sliders_touched = slider_valence.touched
                            error_key = "msg_slider_error_valence"

                        if not sliders_touched and not DEBUG:
                            error_msg = Message.get(error_key)
                        else:
                            running = False

                slider_valence.handle_event(event)
                if slider_arousal is not None:
                    slider_arousal.handle_event(event)

            self.main_screen.fill(WHITE)

            self.draw_slider_label(
                Message.get("msg_valence_label"),
                center_x,
                int(valence_y - self.WINDOW_HEIGHT * 0.11),
            )
            slider_valence.draw(self.main_screen)

            if slider_arousal is not None:
                self.draw_slider_label(
                    Message.get("msg_arousal_label"),
                    center_x,
                    int(arousal_y - self.WINDOW_HEIGHT * 0.11),
                )
                slider_arousal.draw(self.main_screen)

            self.clock.tick(30)

            hover = self.continue_button.rect.collidepoint(
                pygame.mouse.get_pos())
            self.continue_button.draw(self.main_screen, hover=hover)

            if error_msg:
                err_surf = pygame.font.SysFont("arial", max(18, int(self.WINDOW_HEIGHT * 0.03))).render(
                    error_msg, True, RED
                )
                self.main_screen.blit(
                    err_surf, err_surf.get_rect(
                        midtop=(self.WINDOW_WIDTH // 2, int(self.WINDOW_HEIGHT * 0.16)))
                )

            if DEBUG:
                arousal_value = np.nan if slider_arousal is None else slider_arousal.value
                label = pygame.font.SysFont("arial", 25).render(
                    f"Valence: {slider_valence.value:.2f}; Arousal: {arousal_value:.2f}; press ENTER to continue",
                    True,
                    (0, 0, 0),
                )
                self.main_screen.blit(label, (340, 200))

            pygame.display.flip()

        if include_arousal:
            return (slider_valence.value, slider_arousal.value)
        return (slider_valence.value, np.nan)
    # run main game loop: run start screen and drawing app till user closes with exit button

    def run_main_loop(self):
        while rclpy.ok():
            self.activity_start_time = time.time()
            self.activity_started = True
            self.run_study()
            if self.quit:
                exit_program()
            self.reset()


def main(args=None):
    rclpy.init(args=args)
    node = DrawingApplicationNode()
    rclpy.spin(node)  # TODO: spin once? pygame clock?
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
