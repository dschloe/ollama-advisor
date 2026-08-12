"""Tests for system specification detection."""

from unittest.mock import patch

from ollama_advisor import system


def test_usable_gb_cpu_only_uses_ram():
    fake_mem = type("VM", (), {"total": 16 * 1024**3})()
    with patch.object(system.psutil, "virtual_memory", return_value=fake_mem):
        with patch.object(system, "_parse_nvidia_smi", return_value=None):
            with patch.object(system, "_detect_apple_silicon_gpu", return_value=None):
                specs = system.get_system_specs()

    assert specs["gpu"]["type"] == "cpu"
    assert specs["ram_gb"] == 16.0
    assert specs["usable_gb"] == round(16.0 * system.USABLE_RATIO, 2)


def test_is_colab_false_without_module():
    assert system.is_colab() is False


def test_nvidia_gpu_uses_vram_for_usable():
    fake_mem = type("VM", (), {"total": 32 * 1024**3})()
    gpu = {"type": "nvidia", "name": "Test GPU", "vram_gb": 8.0}
    with patch.object(system.psutil, "virtual_memory", return_value=fake_mem):
        with patch.object(system, "_parse_nvidia_smi", return_value=gpu):
            specs = system.get_system_specs()

    assert specs["gpu"]["type"] == "nvidia"
    assert specs["usable_gb"] == round(8.0 * system.USABLE_RATIO, 2)


def test_platform_linux():
    with patch.object(system, "is_colab", return_value=False):
        with patch.object(system.platform, "system", return_value="Linux"):
            assert system._detect_platform() == "linux"
