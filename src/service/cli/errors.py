from copy import deepcopy
from dataclasses import dataclass, field


@dataclass(slots=True)
class CliError(Exception):
    category: str
    message: str
    details: dict | None = field(default=None)

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)
        self.details = deepcopy(self.details) if self.details is not None else None

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "message": self.message,
            "details": deepcopy(self.details or {}),
        }


_EXIT_CODES = {
    "invalid_argument": 2,
    "not_found": 3,
    "conflict": 4,
    "not_ready": 5,
    "version_mismatch": 6,
    "internal_error": 10,
}


def error_to_exit_code(error: CliError) -> int:
    return _EXIT_CODES.get(error.category, 10)
