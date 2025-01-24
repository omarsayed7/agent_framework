import json
import logging
import os

# Load translations
# parent_dir_path = os.path.join(os.path.dirname(__file__), os.pardir)
# translations_file_path = os.path.join(parent_dir_path, "translations.json")
translations_file_path = "/home/omar.sayed@ad.cyshield/Personal/AI/lotionAI/dev/AI Agents/lotionAI_framework/src/connections/telegram/translations.json"

with open(translations_file_path, "r", encoding="utf-8") as f:
    translations = json.load(f)


def localized_text(key, bot_language):
    """
    Return translated text for a key in specified bot_language.
    Keys and translations can be found in the translations.json.
    """
    try:
        return translations[bot_language][key]
    except KeyError:
        logging.warning(
            f"No translation available for bot_language code '{bot_language}' and key '{key}'"
        )
        # Fallback to English if the translation is not available
        if key in translations["en"]:
            return translations["en"][key]
        else:
            logging.warning(
                f"No english definition found for key '{key}' in translations.json"
            )
            # return key as text
            return key
