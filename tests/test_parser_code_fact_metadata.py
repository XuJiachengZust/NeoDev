from gitnexus_parser.ingestion.parser import parse_files


def _find_node(result, label: str, name: str):
    return next(
        node
        for node in result.nodes
        if node.label == label and node.properties.get("name") == name
    )


def test_java_method_metadata_uses_definition_range_and_qualified_name():
    result = parse_files(
        [
            (
                "src/main/java/com/example/AccountService.java",
                "\n".join(
                    [
                        "package com.example;",
                        "",
                        "public class AccountService {",
                        "    public void login(String user) {",
                        "        audit(user);",
                        "    }",
                        "}",
                    ]
                ),
            )
        ]
    )

    class_node = _find_node(result, "Class", "AccountService")
    assert class_node.properties["qualified_name"] == "AccountService"
    assert class_node.properties["startLine"] == 3
    assert class_node.properties["endLine"] == 7

    method_node = _find_node(result, "Method", "login")
    assert method_node.properties["qualified_name"] == "AccountService.login"
    assert method_node.properties["startLine"] == 4
    assert method_node.properties["endLine"] == 6


def test_lua_function_metadata_keeps_simple_name_and_qualified_name():
    result = parse_files(
        [
            (
                "src/access.lua",
                "\n".join(
                    [
                        "function tab.fds._p(ctx)",
                        "    return ctx",
                        "end",
                    ]
                ),
            )
        ]
    )

    function_node = _find_node(result, "Function", "_p")
    assert function_node.properties["qualified_name"] == "tab.fds._p"
    assert function_node.properties["startLine"] == 1
    assert function_node.properties["endLine"] == 3
