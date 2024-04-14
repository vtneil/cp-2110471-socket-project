import os
import re
from datetime import datetime


def datetime_fmt() -> str:
    return datetime.now().strftime('%d/%m/%Y %H:%M:%S')


def tokenize(text: str) -> list[str]:
    pattern = r'"[^"]*"|\S+'
    tokens = re.findall(pattern, text)
    tokens = [token.strip('"') if token.startswith('"') and token.endswith('"') else token for token in tokens]
    return tokens


def uniquify(path: str):
    filename, extension = os.path.splitext(path)
    counter = 1

    while os.path.exists(path):
        path = filename + " (" + str(counter) + ")" + extension
        counter += 1

    return path
