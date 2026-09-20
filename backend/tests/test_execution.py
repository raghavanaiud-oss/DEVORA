from app.execution.runtimes import SUPPORTED_RUNTIMES, detect_runtime


def test_supported_runtimes():
    assert "python" in SUPPORTED_RUNTIMES
    assert "javascript" in SUPPORTED_RUNTIMES
    assert "typescript" in SUPPORTED_RUNTIMES

    py_runtime = SUPPORTED_RUNTIMES["python"]
    assert py_runtime.extension == ".py"
    assert "python" in py_runtime.command


def test_detect_runtime():
    assert detect_runtime("/main.py").name == "python"
    assert detect_runtime("/index.js").name == "javascript"
    assert detect_runtime("/app.ts").name == "typescript"
    assert detect_runtime("/script.unknown", language="python").name == "python"
    assert detect_runtime("/script.unknown").name == "python"  # Default fallback
