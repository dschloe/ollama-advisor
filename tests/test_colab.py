"""Tests for Google Colab Ollama setup helpers."""

from unittest.mock import MagicMock, patch

import pytest

from ollama_advisor.colab import is_server_running, setup_colab_ollama


def test_setup_colab_ollama_raises_outside_colab():
    with patch("ollama_advisor.colab.is_colab", return_value=False):
        with pytest.raises(RuntimeError, match="only for Google Colab"):
            setup_colab_ollama()


def test_setup_colab_ollama_already_running():
    with patch("ollama_advisor.colab.is_colab", return_value=True):
        with patch("ollama_advisor.colab._ensure_apt_deps", return_value=[]):
            with patch("ollama_advisor.colab.is_server_running", return_value=True):
                with patch("ollama_advisor.colab.is_ollama_installed", return_value=True):
                    result = setup_colab_ollama()
    assert result["ready"] is True
    assert result["steps"] == ["already_running"]


def test_setup_colab_ollama_installs_zstd_then_ollama():
    checks = iter([False, False, True, True])

    def fake_running():
        return next(checks)

    with patch("ollama_advisor.colab.is_colab", return_value=True):
        with patch("ollama_advisor.colab._ensure_apt_deps", return_value=["apt:zstd"]) as apt:
            with patch("ollama_advisor.colab.is_ollama_installed", return_value=False):
                with patch("ollama_advisor.colab.subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                    with patch("ollama_advisor.colab.subprocess.Popen"):
                        with patch(
                            "ollama_advisor.colab.is_server_running",
                            side_effect=fake_running,
                        ):
                            with patch("ollama_advisor.colab.time.sleep"):
                                result = setup_colab_ollama(wait_seconds=1)
    apt.assert_called_once()
    assert result["ready"] is True
    assert result["steps"][0] == "apt:zstd"
    assert "installed" in result["steps"]
    assert "started" in result["steps"]


def test_ensure_apt_deps_installs_missing_zstd():
    from ollama_advisor.colab import _ensure_apt_deps

    which_values = iter([None, "/usr/bin/zstd"])

    with patch("ollama_advisor.colab.shutil.which", side_effect=lambda _pkg: next(which_values)):
        with patch("ollama_advisor.colab.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            steps = _ensure_apt_deps()
    assert steps == ["apt:zstd"]
    assert mock_run.call_count == 2
    assert mock_run.call_args_list[0].args[0][:3] == ["sudo", "apt-get", "update"]
    assert "zstd" in mock_run.call_args_list[1].args[0]


def test_ensure_apt_deps_tolerates_unrelated_apt_update_failure():
    """CRAN/r2u mirror sync errors should not block zstd install."""
    from ollama_advisor.colab import _ensure_apt_deps

    which_values = iter([None, "/usr/bin/zstd"])
    update = MagicMock(
        returncode=100,
        stdout="",
        stderr=(
            "E: Failed to fetch https://cloud.r-project.org/bin/linux/ubuntu/"
            "jammy-cran40/Packages.gz File has unexpected size\n"
            "E: Some index files failed to download. They have been ignored, "
            "or old ones used instead.\n"
        ),
    )
    install = MagicMock(returncode=0, stdout="", stderr="")

    with patch("ollama_advisor.colab.shutil.which", side_effect=lambda _pkg: next(which_values)):
        with patch("ollama_advisor.colab.subprocess.run", side_effect=[update, install]) as mock_run:
            steps = _ensure_apt_deps()

    assert steps == ["apt:zstd"]
    assert mock_run.call_count == 2
    assert mock_run.call_args_list[1].args[0][:4] == ["sudo", "apt-get", "install", "-y"]


def test_ensure_apt_deps_raises_when_install_fails_after_update_error():
    from ollama_advisor.ctl import OllamaError
    from ollama_advisor.colab import _ensure_apt_deps

    update = MagicMock(returncode=100, stdout="", stderr="CRAN mirror sync failed")
    install = MagicMock(returncode=100, stdout="", stderr="Unable to locate package zstd")

    with patch("ollama_advisor.colab.shutil.which", return_value=None):
        with patch("ollama_advisor.colab.subprocess.run", side_effect=[update, install]):
            with pytest.raises(OllamaError, match="Failed to install apt packages"):
                _ensure_apt_deps()


def test_is_server_running_false_on_error():
    with patch("ollama_advisor.colab.urllib_request.urlopen", side_effect=OSError("refused")):
        assert is_server_running() is False
