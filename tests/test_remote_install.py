"""Integration tests for remote-install.sh bootstrap script."""

import os
import subprocess

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "remote-install.sh")


class TestSyntax:
    def test_bash_syntax_valid(self):
        """bash -n should pass (no syntax errors)."""
        result = subprocess.run(
            ["bash", "-n", SCRIPT], capture_output=True, text=True
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    def test_shebang(self):
        """Script must start with #!/bin/bash."""
        with open(SCRIPT) as f:
            first_line = f.readline().strip()
        assert first_line == "#!/bin/bash"

    def test_executable(self):
        """Script must have executable permission."""
        assert os.access(SCRIPT, os.X_OK)


class TestHelp:
    def test_help_flag(self):
        """--help should print usage and exit 0."""
        result = subprocess.run(
            ["bash", SCRIPT, "--help"], capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "Usage" in result.stdout
        assert "--ref" in result.stdout

    def test_h_flag(self):
        """-h should behave the same as --help."""
        result = subprocess.run(
            ["bash", SCRIPT, "-h"], capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "Usage" in result.stdout


class TestErrorHandling:
    def test_missing_target_dir(self):
        """Script must fail with clear error when no target dir given."""
        result = subprocess.run(
            ["bash", SCRIPT], capture_output=True, text=True
        )
        assert result.returncode != 0
        assert "No target directory" in result.stderr

    def test_nonexistent_target_dir(self):
        """Script must fail when target dir does not exist."""
        result = subprocess.run(
            ["bash", SCRIPT, "/nonexistent/path/xyz"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "does not exist" in result.stderr

    def test_unknown_option(self):
        """Unknown flags should produce an error."""
        result = subprocess.run(
            ["bash", SCRIPT, "--bogus", "."],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "Unknown option" in result.stderr

    def test_multiple_target_dirs(self):
        """Providing two positional args should error."""
        result = subprocess.run(
            ["bash", SCRIPT, "/tmp", "/tmp"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "Multiple target directories" in result.stderr

    def test_ref_without_value(self):
        """--ref with no value should error."""
        result = subprocess.run(
            ["bash", SCRIPT, "--ref"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "--ref requires" in result.stderr
