from gitnexus_parser.ingestion.import_resolver import (
    build_import_resolver_index,
    resolve_import_path,
)


def test_resolve_import_path_uses_prebuilt_index_for_package_suffixes():
    all_files = {
        "src/main/java/com/acme/app/UserService.java",
        "src/main/java/com/acme/common/User.java",
        "src/test/java/com/acme/common/UserTest.java",
    }
    resolver_index = build_import_resolver_index(all_files)

    resolved = resolve_import_path(
        "src/main/java/com/acme/app/UserService.java",
        "com.acme.common.User",
        all_files,
        resolver_index=resolver_index,
    )

    assert resolved == "src/main/java/com/acme/common/User.java"
