from enum import Enum
import random


class Language(Enum):
    English = "en"
    German = "de"


class Emotions(Enum):
    HAPPINESS = 1
    CONTENTMENT = 2
    ANGER = 3
    SADNESS = 4
    NEUTRAL = 5


class Message:
    @classmethod
    def get(cls, message):
        if message not in cls.messages:
            print(f"Error: {message} does not exist!")
            return message  # display the key that doesn't exist
        if cls.current_lang.value not in cls.messages[message]:
            print(f"Error: {message} was not translated to {cls.current_lang}!")
            # fall back to english
            cls.messages[message][Language.English.value]

        return cls.messages[message][cls.current_lang.value]

    current_lang = Language.English  # default language
    messages = {
        "mood_happy": {"en": "happy", "de": "glücklich"},
        "mood_angry": {"en": "angry", "de": "wütend"},
        "mood_contentment": {"en": "content", "de": "zufrieden"},
        "mood_sad": {"en": "sad", "de": "traurig"},
        "mood_neutral": {"en": "neutral", "de": "neutral"},
    }


def short_string(emos):
    res = ""
    for e in emos:
        res += f"{e[0]},"
    return res[:-1]


mood_map = {
    Emotions.HAPPINESS: Message.get("mood_happy"),
    Emotions.ANGER: Message.get("mood_angry"),
    Emotions.CONTENTMENT: Message.get("mood_contentment"),
    Emotions.SADNESS: Message.get("mood_sad"),
    Emotions.NEUTRAL: Message.get("mood_neutral"),
}

characters = [chr(a) for a in range(ord("A"), ord("Z") + 1)]

N = 30
LENGTH = 4

prev_id = set()

for i in range(N):
    p_id = "".join(random.choice(characters) for i in range(LENGTH))
    while p_id in prev_id:
        p_id = "".join(random.choice(characters) for i in range(LENGTH))
    prev_id.add(p_id)

    positive = random.choice([Emotions.HAPPINESS, Emotions.CONTENTMENT])
    negative = random.choice([Emotions.ANGER, Emotions.SADNESS])
    emotions = [positive, negative, Emotions.NEUTRAL]
    random.shuffle(emotions)
    emotions = [mood_map[e] for e in emotions]

    print(f"{p_id}:    {short_string(emotions)} {emotions}")
