def demo_greeting(name: str) -> str:
    clean_name = name.strip() or "NeoDev"
    return f"Hello, {clean_name}."
