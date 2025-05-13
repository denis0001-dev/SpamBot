import random
import string


def lines(*args: str) -> str: return "\n".join(args)

def generate_long_string(length=4096):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))