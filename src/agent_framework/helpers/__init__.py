import os
import json


def load_character(character_file_path) -> dict:
    """
    Load a character from a specified JSON file.

    Args:
        character_file_path (str): The path to the character JSON file.

    Returns:
        dict: A dictionary containing the character's details, including name, bio, backstory, message examples, and model provider.

    Raises:
        FileNotFoundError: If the specified character file does not exist.
        json.JSONDecodeError: If the file is not a valid JSON.
    """
    # Adjust path to point to your "characters" folder as needed
    character_file_path = os.path.join("./", "characters", character_file_path)
    # Load JSON data
    with open(character_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data
