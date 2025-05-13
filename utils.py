import random
import string


def lines(*args: str) -> str: return "\n".join(args)

def generate_long_string(length=2048):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def escape(string: str) -> str:
    return (string
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("&", "&amp"))
