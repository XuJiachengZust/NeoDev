from gitnexus_parser.ingestion.parser import should_store_source


def test_should_store_source_default_function():
    assert should_store_source(
        language="python",
        label="Function",
        file_path="src/app/service.py",
        name="do_work",
    )


def test_should_store_source_excludes_folder_and_project():
    assert not should_store_source(
        language="python",
        label="Project",
        file_path=".",
        name="proj",
    )
    assert not should_store_source(
        language="python",
        label="Folder",
        file_path="src",
        name="src",
    )


def test_should_store_source_lua_models():
    # Lua model function in models directory
    assert should_store_source(
        language="lua",
        label="Function",
        file_path="game/models/user.lua",
        name="UserModel",
    )
    # Lua non-model function outside models directory should still respect default include for Function
    assert should_store_source(
        language="lua",
        label="Function",
        file_path="game/controllers/user.lua",
        name="handle_request",
    )

