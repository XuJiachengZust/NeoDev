from dataclasses import dataclass, field
from enum import Enum


class CommandVisibility(str, Enum):
    PRIMARY = "primary"
    ADVANCED = "advanced"
    INTERNAL = "internal"
    HIDDEN = "hidden"


@dataclass(frozen=True)
class CommandMetadata:
    path: tuple[str, ...]
    visibility: CommandVisibility
    summary: str
    replacement: str | None = None
    risk: str | None = None
    intents: tuple[str, ...] = field(default_factory=tuple)
    scenarios: tuple[str, ...] = field(default_factory=tuple)

    @property
    def command(self) -> str:
        return "neodev " + " ".join(self.path)

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "path": list(self.path),
            "visibility": self.visibility.value,
            "summary": self.summary,
            "replacement": self.replacement,
            "risk": self.risk,
            "intents": list(self.intents),
            "scenarios": list(self.scenarios),
        }


_COMMANDS: tuple[CommandMetadata, ...] = (
    CommandMetadata(("doctor",), CommandVisibility.PRIMARY, "Check NeoDev local and remote readiness.", intents=("context",), scenarios=("S01",)),
    CommandMetadata(("context", "show"), CommandVisibility.PRIMARY, "Show product, version, project, branch, document, and graph context.", intents=("context",), scenarios=("S01", "S06")),
    CommandMetadata(("setup", "repo"), CommandVisibility.PRIMARY, "Bind the current repository and initialize graph context.", intents=("context",), scenarios=("S01",)),
    CommandMetadata(("docs", "sync"), CommandVisibility.PRIMARY, "Validate and import controlled docs for the current version.", intents=("docs",), scenarios=("S02",)),
    CommandMetadata(("change", "start"), CommandVisibility.PRIMARY, "Register or prepare a DocChange from synced requirements.", intents=("change",), scenarios=("S03",)),
    CommandMetadata(("change", "impact"), CommandVisibility.PRIMARY, "Collect impact and implementation context for a change.", intents=("change", "submit"), scenarios=("S03", "S04")),
    CommandMetadata(("git", "check"), CommandVisibility.PRIMARY, "Check commit scope, DocChange trailer, and commit risks.", intents=("submit",), scenarios=("S04",)),
    CommandMetadata(("status",), CommandVisibility.PRIMARY, "Summarize current NeoDev workflow closure status.", intents=("context", "submit"), scenarios=("S05", "S06")),
    CommandMetadata(("help",), CommandVisibility.ADVANCED, "Show all command visibility metadata."),
    CommandMetadata(("cli", "version-check"), CommandVisibility.ADVANCED, "Check local CLI, plugin, and workflow compatibility.", replacement="neodev doctor"),
    CommandMetadata(("product", "create"), CommandVisibility.ADVANCED, "Create a product atomically."),
    CommandMetadata(("product", "update"), CommandVisibility.ADVANCED, "Update a product atomically."),
    CommandMetadata(("product", "show"), CommandVisibility.ADVANCED, "Show product facts."),
    CommandMetadata(("product", "version", "create"), CommandVisibility.ADVANCED, "Create a product version atomically."),
    CommandMetadata(("product", "version", "show"), CommandVisibility.ADVANCED, "Show product version and branch facts."),
    CommandMetadata(("product", "version", "bind-branch"), CommandVisibility.ADVANCED, "Bind a branch to a product version.", replacement="neodev setup repo"),
    CommandMetadata(("product", "version", "unbind-branch"), CommandVisibility.ADVANCED, "Remove a branch binding from a product version."),
    CommandMetadata(("product", "version", "link-code"), CommandVisibility.ADVANCED, "Manually link a document node to code facts."),
    CommandMetadata(("product", "version", "code-facts"), CommandVisibility.ADVANCED, "Inspect product version code facts."),
    CommandMetadata(("project", "create"), CommandVisibility.ADVANCED, "Create a project atomically.", replacement="neodev setup repo"),
    CommandMetadata(("project", "show"), CommandVisibility.ADVANCED, "Show project facts.", replacement="neodev context show"),
    CommandMetadata(("project", "refresh-graph"), CommandVisibility.ADVANCED, "Refresh a project branch graph manually.", replacement="neodev status"),
    CommandMetadata(("project", "init-status"), CommandVisibility.ADVANCED, "Show project graph initialization status.", replacement="neodev status"),
    CommandMetadata(("doc", "binding", "create"), CommandVisibility.ADVANCED, "Create a document binding.", replacement="neodev docs sync"),
    CommandMetadata(("doc", "binding", "list"), CommandVisibility.ADVANCED, "List document bindings.", replacement="neodev context show"),
    CommandMetadata(("doc", "binding", "switch"), CommandVisibility.ADVANCED, "Switch a document binding."),
    CommandMetadata(("doc", "graph", "show"), CommandVisibility.ADVANCED, "Show document graph facts.", replacement="neodev status"),
    CommandMetadata(("doc", "scan"), CommandVisibility.ADVANCED, "Scan controlled docs.", replacement="neodev docs sync"),
    CommandMetadata(("doc", "import"), CommandVisibility.ADVANCED, "Import controlled docs.", replacement="neodev docs sync"),
    CommandMetadata(("doc", "change", "register"), CommandVisibility.ADVANCED, "Register a DocChange.", replacement="neodev change start"),
    CommandMetadata(("doc", "change", "show"), CommandVisibility.ADVANCED, "Show a DocChange.", replacement="neodev status"),
    CommandMetadata(("doc", "change", "mark-implemented"), CommandVisibility.ADVANCED, "Mark a DocChange implemented."),
    CommandMetadata(("graph", "impact"), CommandVisibility.ADVANCED, "Run graph impact analysis.", replacement="neodev change impact"),
    CommandMetadata(("graph", "entity-context"), CommandVisibility.ADVANCED, "Read graph entity context.", replacement="neodev change impact"),
    CommandMetadata(("graph", "get-chain"), CommandVisibility.ADVANCED, "Read graph chain context.", replacement="neodev change impact"),
    CommandMetadata(("graph", "type", "node", "add"), CommandVisibility.ADVANCED, "Add a manual graph node type.", risk="manual graph mutation"),
    CommandMetadata(("graph", "type", "node", "list"), CommandVisibility.ADVANCED, "List graph node types."),
    CommandMetadata(("graph", "type", "node", "archive"), CommandVisibility.ADVANCED, "Archive a graph node type.", risk="manual graph mutation"),
    CommandMetadata(("graph", "type", "edge", "add"), CommandVisibility.ADVANCED, "Add a manual graph edge type.", risk="manual graph mutation"),
    CommandMetadata(("graph", "type", "edge", "list"), CommandVisibility.ADVANCED, "List graph edge types."),
    CommandMetadata(("graph", "type", "edge", "archive"), CommandVisibility.ADVANCED, "Archive a graph edge type.", risk="manual graph mutation"),
    CommandMetadata(("graph", "node", "add"), CommandVisibility.ADVANCED, "Add a manual graph node.", risk="manual graph mutation"),
    CommandMetadata(("graph", "node", "update"), CommandVisibility.ADVANCED, "Update a manual graph node.", risk="manual graph mutation"),
    CommandMetadata(("graph", "node", "delete"), CommandVisibility.ADVANCED, "Archive a manual graph node.", risk="manual graph mutation"),
    CommandMetadata(("graph", "node", "show"), CommandVisibility.ADVANCED, "Show a manual graph node."),
    CommandMetadata(("graph", "node", "list"), CommandVisibility.ADVANCED, "List manual graph nodes."),
    CommandMetadata(("graph", "edge", "add"), CommandVisibility.ADVANCED, "Add a manual graph edge.", risk="manual graph mutation"),
    CommandMetadata(("graph", "edge", "update"), CommandVisibility.ADVANCED, "Update a manual graph edge.", risk="manual graph mutation"),
    CommandMetadata(("graph", "edge", "delete"), CommandVisibility.ADVANCED, "Archive a manual graph edge.", risk="manual graph mutation"),
    CommandMetadata(("graph", "edge", "show"), CommandVisibility.ADVANCED, "Show a manual graph edge."),
    CommandMetadata(("graph", "edge", "list"), CommandVisibility.ADVANCED, "List manual graph edges."),
    CommandMetadata(("git", "verify-doc-change"), CommandVisibility.ADVANCED, "Verify a commit DocChange trailer.", replacement="neodev git check"),
    CommandMetadata(("git", "dangerous-commit", "list"), CommandVisibility.ADVANCED, "List dangerous commit records.", replacement="neodev git check"),
    CommandMetadata(("git", "dangerous-commit", "resolve"), CommandVisibility.ADVANCED, "Resolve a dangerous commit record.", risk="risk override"),
    CommandMetadata(("git", "post-push-graph-update"), CommandVisibility.INTERNAL, "Apply the atomic post-push graph update.", replacement="neodev status", risk="hook-only"),
    CommandMetadata(("product", "version", "analyze"), CommandVisibility.HIDDEN, "Legacy branch analysis command.", replacement="neodev setup repo"),
    CommandMetadata(("product", "version", "analyze-status"), CommandVisibility.HIDDEN, "Legacy branch analysis status command.", replacement="neodev status"),
    CommandMetadata(("product", "version", "watch-status"), CommandVisibility.HIDDEN, "Legacy branch analysis watch command.", replacement="neodev status"),
)


def get_command_metadata() -> tuple[CommandMetadata, ...]:
    return _COMMANDS


def get_command_metadata_payload() -> dict:
    return {
        "visibility_levels": [item.value for item in CommandVisibility],
        "commands": [item.to_dict() for item in _COMMANDS],
    }
