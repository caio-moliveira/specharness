from specharness_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "specharness" in result.output
