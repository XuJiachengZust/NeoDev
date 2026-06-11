from collections import defaultdict

from service.cli.command_metadata import CommandVisibility, get_command_metadata


_HEADERS = {
    CommandVisibility.PRIMARY: "Primary",
    CommandVisibility.ADVANCED: "Advanced",
    CommandVisibility.INTERNAL: "Internal",
    CommandVisibility.HIDDEN: "Hidden",
}


def render_default_help() -> str:
    lines = ["NeoDev primary commands:"]
    for item in get_command_metadata():
        if item.visibility is CommandVisibility.PRIMARY:
            lines.append(f"  {item.command:<32} {item.summary}")
    lines.extend(
        [
            "",
            "Run `neodev help --all` to show advanced, internal, and hidden commands.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_all_help() -> str:
    grouped = defaultdict(list)
    for item in get_command_metadata():
        grouped[item.visibility].append(item)

    lines: list[str] = []
    for visibility in CommandVisibility:
        lines.append(f"{_HEADERS[visibility]}:")
        for item in grouped.get(visibility, []):
            suffixes = []
            if item.replacement:
                suffixes.append(f"replacement={item.replacement}")
            if item.risk:
                suffixes.append(f"risk={item.risk}")
            suffix = f" ({'; '.join(suffixes)})" if suffixes else ""
            lines.append(f"  {item.command:<42} visibility={item.visibility.value} - {item.summary}{suffix}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
