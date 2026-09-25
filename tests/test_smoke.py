from pathlib import Path


def test_project_folders_exist():
    """Verify expected top-level folders exist."""
    base_dir = Path(__file__).parent.parent
    expected_folders = [
        "data",
        "notebooks",
        "edge",
        "simulation",
        "ml",
        "mlops",
        "tests",
        "docs",
    ]
    for folder in expected_folders:
        assert (base_dir / folder).is_dir(), f"Expected folder '{folder}' does not exist"


def test_env_example_secrets_empty():
    """Verify .env.example contains no populated values for secret-like keys."""
    env_example_path = Path(__file__).parent.parent / ".env.example"
    assert env_example_path.is_file(), ".env.example file is missing"

    secret_keys = ["JWT_SECRET", "MQTT_PASSWORD", "DATABASE_URL"]

    with open(env_example_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            if key in secret_keys:
                assert (
                    value.strip() == ""
                ), f"Secret key '{key}' should not have a populated value in .env.example"
