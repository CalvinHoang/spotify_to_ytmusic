import pytest
import json
from spotify2ytmusic import gui_utils # Imports the module where helper functions are

# Test cases for parse_settings_data
def test_parse_settings_data_valid_json():
    """Test parsing valid JSON content."""
    json_content = '{"auto_scroll": false, "algo_number": 1}'
    expected = {"auto_scroll": False, "algo_number": 1}
    assert gui_utils.parse_settings_data(json_content, gui_utils.DEFAULT_SETTINGS_VALUES) == expected

def test_parse_settings_data_empty_json():
    """Test parsing empty JSON content, should return defaults."""
    json_content = ""
    assert gui_utils.parse_settings_data(json_content, gui_utils.DEFAULT_SETTINGS_VALUES) == gui_utils.DEFAULT_SETTINGS_VALUES

def test_parse_settings_data_malformed_json(capsys):
    """Test parsing malformed JSON content, should return defaults and print warning."""
    json_content = '{"auto_scroll": false, "algo_number": 1' # Missing closing brace
    assert gui_utils.parse_settings_data(json_content, gui_utils.DEFAULT_SETTINGS_VALUES) == gui_utils.DEFAULT_SETTINGS_VALUES
    captured = capsys.readouterr()
    assert "Warning: JSONDecodeError while parsing settings. Using defaults." in captured.out

def test_parse_settings_data_missing_keys():
    """Test JSON with missing keys, should use defaults for those keys."""
    json_content = '{"auto_scroll": true}' # algo_number is missing
    expected = {"auto_scroll": True, "algo_number": gui_utils.DEFAULT_SETTINGS_VALUES["algo_number"]}
    assert gui_utils.parse_settings_data(json_content, gui_utils.DEFAULT_SETTINGS_VALUES) == expected

def test_parse_settings_data_extra_keys():
    """Test JSON with extra keys.
    Current parse_settings_data implementation using dict.update() will include these extra keys.
    """
    json_content = '{"auto_scroll": false, "algo_number": 2, "extra_key": "value"}'
    # Based on: final_settings = default_settings.copy(); final_settings.update(loaded_settings)
    # Extra keys from loaded_settings will be present in the result.
    expected_with_extra = {"auto_scroll": False, "algo_number": 2, "extra_key": "value"}
    # However, DEFAULT_SETTINGS_VALUES only has 'auto_scroll' and 'algo_number'.
    # The update mechanism will add 'extra_key' to the copied default_settings.
    assert gui_utils.parse_settings_data(json_content, gui_utils.DEFAULT_SETTINGS_VALUES) == expected_with_extra

def test_parse_settings_data_different_valid_values():
    """Test with different valid values to ensure they are parsed correctly."""
    json_content = '{"auto_scroll": true, "algo_number": 2}'
    expected = {"auto_scroll": True, "algo_number": 2}
    assert gui_utils.parse_settings_data(json_content, gui_utils.DEFAULT_SETTINGS_VALUES) == expected


# Test cases for prepare_settings_for_save
def test_prepare_settings_for_save_case_1():
    """Test preparing settings dict with True and 0."""
    expected = {"auto_scroll": True, "algo_number": 0}
    assert gui_utils.prepare_settings_for_save(True, 0) == expected

def test_prepare_settings_for_save_case_2():
    """Test preparing settings dict with False and 2."""
    expected = {"auto_scroll": False, "algo_number": 2}
    assert gui_utils.prepare_settings_for_save(False, 2) == expected

def test_prepare_settings_for_save_other_values():
    """Test preparing settings dict with different algo number."""
    expected = {"auto_scroll": True, "algo_number": 1}
    assert gui_utils.prepare_settings_for_save(True, 1) == expected

# Test for DEFAULT_SETTINGS_VALUES (simple check)
def test_default_settings_values_content():
    """Check the content of DEFAULT_SETTINGS_VALUES."""
    # This test will fail if gui.DEFAULT_SETTINGS_VALUES is not the same as the one in gui_utils
    # After refactoring, this should ideally test gui_utils.DEFAULT_SETTINGS_VALUES
    assert gui_utils.DEFAULT_SETTINGS_VALUES == {"auto_scroll": True, "algo_number": 0}


# Test with mocker for json.loads for more fine-grained error simulation if needed
def test_parse_settings_data_json_decode_error_mocked(mocker, capsys):
    """Test JSONDecodeError specifically mocked."""
    mocker.patch('json.loads', side_effect=json.JSONDecodeError("Mocked error", "doc", 0))
    json_content = '{"auto_scroll": false, "algo_number": 1}' # Content doesn't matter due to mock
    assert gui_utils.parse_settings_data(json_content, gui_utils.DEFAULT_SETTINGS_VALUES) == gui_utils.DEFAULT_SETTINGS_VALUES
    captured = capsys.readouterr()
    assert "Warning: JSONDecodeError while parsing settings. Using defaults." in captured.out

# Ensure the module can be imported (basic check for syntax errors not caught by linter)
# This test will also change once 'gui' is replaced by 'gui_utils'
def test_module_importable():
    from spotify2ytmusic import gui_utils as gu
    assert gu.DEFAULT_SETTINGS_VALUES is not None
    assert callable(gu.parse_settings_data)
    assert callable(gu.prepare_settings_for_save)

# The test `test_parse_settings_data_extra_keys` was written to expect extra keys
# to be present in the output. This is correct based on `dict.update()` behavior.
# The original code, by using `settings.get("key", default)`, implicitly ignored extra keys
# at the point of *use*, not at the point of *loading*. The refactored `parse_settings_data`
# now returns a dictionary that might contain these extra keys if they were in the JSON.
# The `Window._load_settings` method then uses this dictionary to set specific Tkinter
# variables, effectively ignoring the extra keys at that stage, similar to the original.
# So, the current behavior of `parse_settings_data` is fine.
