# translator.py – UI string localization

"""Provides a simple dictionary of UI strings per language.

The UI reads strings via ``get_ui_strings(lang_code)`` and falls back to English.
Only a handful of labels are needed for the MVP; additional keys can be added
as the UI expands.
"""

from typing import Dict

UI_STRINGS: Dict[str, Dict[str, str]] = {
    "en": {
        "title": "Bureaucracy Autopilot",
        "placeholder": "Type your request…",
        "send": "Send",
        "download": "Download Official Form",
        "language": "Language",
        "thinking": "Thinking...",
        "error": "Oops! Something went wrong.",
        "required_missing": "Please provide the missing information: {field}",
    },
    "hi": {
        "title": "ब्यूरोक्रेसी ऑटोपायलट",
        "placeholder": "अपना अनुरोध लिखें…",
        "send": "भेजें",
        "download": "अधिकारिक फॉर्म डाउनलोड करें",
        "language": "भाषा",
        "thinking": "सोच रहा हूँ…",
        "error": "ओह! कुछ गड़बड़ हुई।",
        "required_missing": "कृपया अनुपलब्ध जानकारी प्रदान करें: {field}",
    },
    "bn": {
        "title": "বিউরোক্রেসি অটোপাইলট",
        "placeholder": "আপনার অনুরোধ লিখুন…",
        "send": "পাঠান",
        "download": "অফিসিয়াল ফর্ম ডাউনলোড",
        "language": "ভাষা",
        "thinking": "ভাবনা চলছে…",
        "error": "উফ! কিছু ভুল হয়েছে।",
        "required_missing": "অনুগ্রহ করে অনুপস্থিত তথ্য দিন: {field}",
    },
    # Add more languages as needed
}

def get_ui_strings(lang_code: str) -> Dict[str, str]:
    """Return the UI strings for *lang_code* (e.g. "en", "hi", "bn").
    Falls back to English if the language is not defined.
    """
    return UI_STRINGS.get(lang_code, UI_STRINGS["en"])
