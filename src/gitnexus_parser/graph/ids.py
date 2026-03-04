"""ID generation aligned with gitnexus/src/lib/utils.ts: {Label}:{Name}."""


def generate_id(label: str, name: str) -> str:
    """Generate node/relationship id. Format: {Label}:{Name}."""
    return f"{label}:{name}"
