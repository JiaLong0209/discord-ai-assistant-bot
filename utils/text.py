import re

import logging

# Configure logging (usually at the top of your main module)
logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG to see debug messages
    # level=logging.DEBUG,  # Set to DEBUG to see debug messages
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)


TIME_TAG_PATTERN = re.compile(r'\[time: .*?\]\s*')
PARENS_PATTERN = re.compile(r"\([^)]*\)")
MENTION_PATTERN = re.compile(r"<@!?\d+>")  # matches <@123> or <@!123>


CHINESE_PATTERN = re.compile(r'[\u4E00-\u9FFF\u3400-\u4DBF\uF900-\uFAFF]')
LETTER_PATTERN = re.compile(r'[\u4E00-\u9FFF\u3400-\u4DBF\uF900-\uFAFF\u3040-\u309F\u30A0-\u30FF]')


def remove_time_tag(text: str) -> str:
    """Remove `[time: ...]` tags from a string."""
    return TIME_TAG_PATTERN.sub('', text)

def remove_discord_mentions(text: str) -> str:
    """Remove Discord user mentions like <@123456789>."""
    return MENTION_PATTERN.sub("", text).strip()

def remove_parentheses(text: str) -> str:
    """Remove anything inside parentheses (including the parentheses)."""
    return PARENS_PATTERN.sub("", text).strip()

def remove_chinese_sentences(text: str, chinese_ratio_threshold: float = 0.95) -> str:
    sentences = re.split(r'(?<=[。！？…])', text)
    result = []

    logger.debug("Sentences after split: %s", sentences)

    for s in sentences:
        logger.debug("Processing sentence: %s", s)
        letters = LETTER_PATTERN.findall(s)
        chinese_chars = CHINESE_PATTERN.findall(s)

        logger.debug("Letters (%d): %s", len(letters), letters)
        logger.debug("Chinese chars (%d): %s", len(chinese_chars), chinese_chars)

        if not letters:
            logger.debug("No letters, appending sentence: %s", s.strip())
            result.append(s.strip())
            continue

        if len(chinese_chars) / len(letters) > chinese_ratio_threshold:
            logger.debug("Sentence skipped due to high Chinese ratio: %s", s.strip())
            continue

        logger.debug("Appending sentence: %s", s.strip())
        result.append(s.strip())

    result_text = "".join(result)
    logger.debug("Final result: %s", result_text)
    return result_text

def extract_japanese_text(text: str, chinese_ratio_threshold: float = 0.95) -> str:
    return  remove_chinese_sentences(remove_parentheses(remove_discord_mentions(remove_time_tag(text))))
