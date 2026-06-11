def hide_subparser_choices(subparsers, hidden_names: set[str]) -> None:
    subparsers._choices_actions = [
        action for action in subparsers._choices_actions if action.dest not in hidden_names
    ]
