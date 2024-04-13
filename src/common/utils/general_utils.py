import re
from datetime import datetime


def datetime_fmt() -> str:
    return datetime.now().strftime('%d/%m/%Y %H:%M:%S')


def tokenize(text) -> list[str]:
    pattern = r'"[^"]*"|\S+'
    tokens = re.findall(pattern, text)
    tokens = [token.strip('"') if token.startswith('"') and token.endswith('"') else token for token in tokens]
    return tokens
