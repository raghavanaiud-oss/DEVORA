from app.services.file_service import detect_language, normalize_path


def test_detect_language():
    assert detect_language("/src/main.py") == "python"
    assert detect_language("app.ts") == "typescript"
    assert detect_language("component.jsx") == "javascript"
    assert detect_language("main.go") == "go"
    assert detect_language("lib.rs") == "rust"
    assert detect_language("server.cpp") == "cpp"
    assert detect_language("README.md") == "markdown"
    assert detect_language("config.json") == "json"
    assert detect_language("unknown.xyz") == "plaintext"


def test_normalize_path():
    assert normalize_path("main.py") == "/main.py"
    assert normalize_path("/src/utils/helpers.py") == "/src/utils/helpers.py"
    assert normalize_path("src/../src/main.py") == "/src/main.py"
    assert normalize_path("/a/b/../../c.py") == "/c.py"
