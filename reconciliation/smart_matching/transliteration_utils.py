"""
Transliteration Utilities

Shared transliteration functions for Mongolian/Cyrillic to Latin conversion
Used across all smart matching engines for consistent character handling.
"""

import re
from typing import Dict, List


class TransliterationUtils:
    """Utility class for Cyrillic-Latin transliteration in Mongolian context"""

    def __init__(self):
        # Cyrillic to Latin transliteration mapping for Mongolian
        self.cyrillic_to_latin = {
            "А": "A",
            "Б": "B",
            "В": "V",
            "Г": "G",
            "Д": "D",
            "Е": "E",
            "Ё": "YO",
            "Ж": "ZH",
            "З": "Z",
            "И": "I",
            "Й": "Y",
            "К": "K",
            "Л": "L",
            "М": "M",
            "Н": "N",
            "О": "O",
            "П": "P",
            "Р": "R",
            "С": "S",
            "Т": "T",
            "У": "U",
            "Ф": "F",
            "Х": "KH",
            "Ц": "TS",
            "Ч": "CH",
            "Ш": "SH",
            "Щ": "SHCH",
            "Ъ": "",
            "Ы": "Y",
            "Ь": "",
            "Э": "E",
            "Ю": "YU",
            "Я": "YA",
            "Ө": "U",  # Mongolian specific - Ө = U (not O)
            "Ү": "U",  # Mongolian specific
        }

        # Character variations for flexible matching
        self.character_variations = {
            "U": ["У", "Ү", "Ө"],  # U can match У, Ү, or Ө
            "Y": ["У", "Ү", "Ы", "Й"],  # Y can match various Cyrillic letters
            "O": ["О"],  # O can only match О (not Ө)
            "C": ["Ч", "С"],  # C can match Ч or С
            "L": ["Л"],  # L matches Л
            "T": ["Т"],  # T matches Т
            "Z": ["З"],  # Z matches З
        }

        # Common ID letter combinations and their variations
        self.id_prefixes = {
            "ЧЛ": ["CL", "ChL", "CH", "TsL"],
            "ТЗ": ["TZ", "T3", "T2"],
            "УТ": ["UT", "YT"],
            "МУ": ["MU", "MY"],
        }

    def transliterate_to_latin(self, cyrillic_text: str) -> str:
        """Convert Cyrillic text to Latin"""
        result = cyrillic_text.upper()

        # Handle individual character transliteration
        for cyrillic, latin in self.cyrillic_to_latin.items():
            result = result.replace(cyrillic, latin)

        return result

    def transliterate_to_cyrillic(self, latin_text: str) -> str:
        """Convert Latin text to Cyrillic using reverse mapping and variations"""
        result = latin_text.upper()

        # Handle character variations (U, Y can match multiple Cyrillic letters)
        for latin_char, cyrillic_options in self.character_variations.items():
            if latin_char in result:
                # Use the most common Cyrillic equivalent
                primary_cyrillic = cyrillic_options[0]
                result = result.replace(latin_char, primary_cyrillic)

        # Handle individual character transliteration for remaining characters
        # Create a proper reverse mapping
        latin_to_cyrillic = {}
        for cyrillic, latin in self.cyrillic_to_latin.items():
            if (
                latin and latin not in latin_to_cyrillic
            ):  # Avoid empty strings and duplicates
                latin_to_cyrillic[latin] = cyrillic

        # Apply character-by-character transliteration
        for latin, cyrillic in latin_to_cyrillic.items():
            result = result.replace(latin, cyrillic)

        return result

    def normalize_name(self, name: str) -> List[str]:
        """Generate name variations for flexible matching"""
        variations = [name.upper()]

        # Add Latin transliteration
        latin_version = self.transliterate_to_latin(name)
        if latin_version != name.upper():
            variations.append(latin_version)

        # Add Cyrillic transliteration
        cyrillic_version = self.transliterate_to_cyrillic(name)
        if cyrillic_version != name.upper():
            variations.append(cyrillic_version)

        return list(set(variations))  # Remove duplicates

    def normalize_id_prefix(self, id_text: str) -> List[str]:
        """Generate ID prefix variations for flexible matching"""
        id_upper = id_text.upper()
        variations = [id_upper]

        # Check if it starts with any known ID prefix
        for cyrillic_prefix, latin_variants in self.id_prefixes.items():
            if id_upper.startswith(cyrillic_prefix):
                # Add Latin variants
                number_part = id_upper[len(cyrillic_prefix) :]
                for latin_variant in latin_variants:
                    variations.append(latin_variant + number_part)
            else:
                # Check if it starts with any Latin variant
                for latin_variant in latin_variants:
                    if id_upper.startswith(latin_variant):
                        number_part = id_upper[len(latin_variant) :]
                        variations.append(cyrillic_prefix + number_part)
                        break

        return list(set(variations))

    def flexible_match(self, input_text: str, db_text: str) -> bool:
        """Check if two texts match using transliteration flexibility"""
        if not input_text or not db_text:
            return False

        input_clean = input_text.replace("-", "").replace(" ", "").upper()
        db_clean = db_text.replace("-", "").replace(" ", "").upper()

        # Direct match
        if input_clean == db_clean:
            return True

        # Transliterate input and compare
        input_latin = self.transliterate_to_latin(input_clean)
        input_cyrillic = self.transliterate_to_cyrillic(input_clean)

        # Transliterate database text and compare
        db_latin = self.transliterate_to_latin(db_clean)
        db_cyrillic = self.transliterate_to_cyrillic(db_clean)

        # Check all combinations
        return any(
            [
                input_clean == db_latin,
                input_clean == db_cyrillic,
                input_latin == db_clean,
                input_latin == db_latin,
                input_latin == db_cyrillic,
                input_cyrillic == db_clean,
                input_cyrillic == db_latin,
                input_cyrillic == db_cyrillic,
            ]
        )


# Global instance for shared use
transliteration = TransliterationUtils()
