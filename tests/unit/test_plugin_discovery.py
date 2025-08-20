"""
Unit tests for plugin discovery
"""

import importlib.metadata

import pytest


@pytest.mark.unit
def test_plugin_entry_points_exist():
    """Test that plugin entry points are properly registered"""
    eps = importlib.metadata.entry_points()

    # Get entry points
    if hasattr(eps, "select"):
        move_plugins = list(eps.select(group="pymodaq.move_plugins"))
        viewer_plugins = list(eps.select(group="pymodaq.viewer_plugins"))
    else:
        move_plugins = eps.get("pymodaq.move_plugins", [])
        viewer_plugins = eps.get("pymodaq.viewer_plugins", [])

    # Find URASHG plugins
    urashg_move = [
        ep
        for ep in move_plugins
        if "urashg" in ep.value.lower()
        or any(x in ep.name.lower() for x in ["maitai", "elliptec", "esp300"])
    ]
    urashg_viewer = [
        ep
        for ep in viewer_plugins
        if "urashg" in ep.value.lower()
        or any(x in ep.name.lower() for x in ["newport", "prime"])
    ]

    # Check we have expected plugins
    assert (
        len(urashg_move) >= 3
    ), f"Expected at least 3 move plugins, found {len(urashg_move)}"
    assert (
        len(urashg_viewer) >= 2
    ), f"Expected at least 2 viewer plugins, found {len(urashg_viewer)}"


@pytest.mark.unit
def test_move_plugin_entry_points_loadable():
    """Test that move plugin entry points can be loaded"""
    eps = importlib.metadata.entry_points()

    expected_plugins = ["DAQ_Move_MaiTai", "DAQ_Move_Elliptec", "DAQ_Move_ESP300"]

    for plugin_name in expected_plugins:
        if hasattr(eps, "select"):
            ep_list = list(eps.select(group="pymodaq.move_plugins", name=plugin_name))
        else:
            ep_list = [
                ep
                for ep in eps.get("pymodaq.move_plugins", [])
                if ep.name == plugin_name
            ]

        assert len(ep_list) > 0, f"Entry point for {plugin_name} not found"

        # Try to load the plugin class
        plugin_class = ep_list[0].load()
        assert plugin_class is not None, f"Failed to load {plugin_name}"


@pytest.mark.unit
def test_viewer_plugin_entry_points_loadable():
    """Test that viewer plugin entry points can be loaded"""
    eps = importlib.metadata.entry_points()

    expected_plugins = ["DAQ_0DViewer_Newport1830C", "DAQ_2DViewer_PrimeBSI"]

    for plugin_name in expected_plugins:
        if hasattr(eps, "select"):
            ep_list = list(eps.select(group="pymodaq.viewer_plugins", name=plugin_name))
        else:
            ep_list = [
                ep
                for ep in eps.get("pymodaq.viewer_plugins", [])
                if ep.name == plugin_name
            ]

        assert len(ep_list) > 0, f"Entry point for {plugin_name} not found"

        # Try to load the plugin class
        plugin_class = ep_list[0].load()
        assert plugin_class is not None, f"Failed to load {plugin_name}"
