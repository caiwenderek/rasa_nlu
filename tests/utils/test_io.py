import os
import io
import pytest
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError

import rasa.utils.io as io_utils

os.environ["USER_NAME"] = "user"
os.environ["PASS"] = "pass"


def test_read_yaml_string():
    config_without_env_var = """
    user: user
    password: pass
    """
    content = io_utils.read_yaml(config_without_env_var)
    assert content["user"] == "user" and content["password"] == "pass"


def test_read_yaml_string_with_env_var():
    config_with_env_var = """
    user: ${USER_NAME}
    password: ${PASS}
    """
    content = io_utils.read_yaml(config_with_env_var)
    assert content["user"] == "user" and content["password"] == "pass"


def test_read_yaml_string_with_multiple_env_vars_per_line():
    config_with_env_var = """
    user: ${USER_NAME} ${PASS}
    password: ${PASS}
    """
    content = io_utils.read_yaml(config_with_env_var)
    assert content["user"] == "user pass" and content["password"] == "pass"


def test_read_yaml_string_with_env_var_prefix():
    config_with_env_var_prefix = """
    user: db_${USER_NAME}
    password: db_${PASS}
    """
    content = io_utils.read_yaml(config_with_env_var_prefix)
    assert content["user"] == "db_user" and content["password"] == "db_pass"


def test_read_yaml_string_with_env_var_postfix():
    config_with_env_var_postfix = """
    user: ${USER_NAME}_admin
    password: ${PASS}_admin
    """
    content = io_utils.read_yaml(config_with_env_var_postfix)
    assert content["user"] == "user_admin" and content["password"] == "pass_admin"


def test_read_yaml_string_with_env_var_infix():
    config_with_env_var_infix = """
    user: db_${USER_NAME}_admin
    password: db_${PASS}_admin
    """
    content = io_utils.read_yaml(config_with_env_var_infix)
    assert content["user"] == "db_user_admin" and content["password"] == "db_pass_admin"


def test_read_yaml_string_with_env_var_not_exist():
    config_with_env_var_not_exist = """
    user: ${USER_NAME}
    password: ${PASSWORD}
    """
    with pytest.raises(ValueError):
        io_utils.read_yaml(config_with_env_var_not_exist)


def test_environment_variable_not_existing():
    content = "model: \n  test: ${variable}"
    with pytest.raises(ValueError):
        io_utils.read_yaml(content)


def test_environment_variable_dict_without_prefix_and_postfix():
    os.environ["variable"] = "test"
    content = "model: \n  test: ${variable}"

    content = io_utils.read_yaml(content)

    assert content["model"]["test"] == "test"


def test_environment_variable_in_list():
    os.environ["variable"] = "test"
    content = "model: \n  - value\n  - ${variable}"

    content = io_utils.read_yaml(content)

    assert content["model"][1] == "test"


def test_environment_variable_dict_with_prefix():
    os.environ["variable"] = "test"
    content = "model: \n  test: dir/${variable}"

    content = io_utils.read_yaml(content)

    assert content["model"]["test"] == "dir/test"


def test_environment_variable_dict_with_postfix():
    os.environ["variable"] = "test"
    content = "model: \n  test: ${variable}/dir"

    content = io_utils.read_yaml(content)

    assert content["model"]["test"] == "test/dir"


def test_environment_variable_dict_with_prefix_and_with_postfix():
    os.environ["variable"] = "test"
    content = "model: \n  test: dir/${variable}/dir"

    content = io_utils.read_yaml(content)

    assert content["model"]["test"] == "dir/test/dir"


def test_emojis_in_yaml():
    test_data = """
    data:
        - one 😁💯 👩🏿‍💻👨🏿‍💻
        - two £ (?u)\\b\\w+\\b f\u00fcr
    """
    content = io_utils.read_yaml(test_data)

    assert content["data"][0] == "one 😁💯 👩🏿‍💻👨🏿‍💻"
    assert content["data"][1] == "two £ (?u)\\b\\w+\\b für"


def test_emojis_in_tmp_file():
    test_data = """
        data:
            - one 😁💯 👩🏿‍💻👨🏿‍💻
            - two £ (?u)\\b\\w+\\b f\u00fcr
        """
    test_file = io_utils.create_temporary_file(test_data)
    with io.open(test_file, mode="r", encoding="utf-8") as f:
        content = f.read()
    content = io_utils.read_yaml(content)

    assert content["data"][0] == "one 😁💯 👩🏿‍💻👨🏿‍💻"
    assert content["data"][1] == "two £ (?u)\\b\\w+\\b für"


def test_read_emojis_from_json():
    import json

    d = {"text": "hey 😁💯 👩🏿‍💻👨🏿‍💻🧜‍♂️(?u)\\b\\w+\\b} f\u00fcr"}
    json_string = json.dumps(d, indent=2)

    content = io_utils.read_yaml(json_string)

    expected = "hey 😁💯 👩🏿‍💻👨🏿‍💻🧜‍♂️(?u)\\b\\w+\\b} für"
    assert content.get("text") == expected


def test_bool_str():
    test_data = """
    one: "yes"
    two: "true"
    three: "True"
    """

    content = io_utils.read_yaml(test_data)

    assert content["one"] == "yes"
    assert content["two"] == "true"
    assert content["three"] == "True"


def test_read_file_with_not_existing_path():
    with pytest.raises(ValueError):
        io_utils.read_file("some path")


@pytest.mark.parametrize("file, parents", [("A/test.md", "A"), ("A", "A")])
def test_file_in_path(file, parents):
    assert io_utils.is_subdirectory(file, parents)


@pytest.mark.parametrize(
    "file, parents", [("A", "A/B"), ("B", "A"), ("A/test.md", "A/B"), (None, "A")]
)
def test_file_not_in_path(file, parents):
    assert not io_utils.is_subdirectory(file, parents)


@pytest.mark.parametrize("actual_path", ["", "file.md", "file"])
def test_file_path_validator_with_invalid_paths(actual_path):

    test_error_message = actual_path

    validator = io_utils.file_type_validator([".yml"], test_error_message)

    document = Document(actual_path)
    with pytest.raises(ValidationError) as e:
        validator.validate(document)

    assert e.value.message == test_error_message


@pytest.mark.parametrize("actual_path", ["domain.yml", "lala.yaml"])
def test_file_path_validator_with_valid_paths(actual_path):

    validator = io_utils.file_type_validator([".yml", ".yaml"], "error message")

    document = Document(actual_path)
    # If the path is valid there shouldn't be an exception
    assert validator.validate(document) is None


@pytest.mark.parametrize("user_input", ["", "   ", "\t", "\n"])
def test_non_empty_text_validator_with_empty_input(user_input):

    test_error_message = "enter something"

    validator = io_utils.not_empty_validator(test_error_message)

    document = Document(user_input)
    with pytest.raises(ValidationError) as e:
        validator.validate(document)

    assert e.value.message == test_error_message


@pytest.mark.parametrize("user_input", ["utter_greet", "greet", "Hi there!"])
def test_non_empty_text_validator_with_valid_input(user_input):

    validator = io_utils.not_empty_validator("error message")

    document = Document(user_input)
    # If there is input there shouldn't be an exception
    assert validator.validate(document) is None


def test_create_validator_from_callable():
    def is_valid(user_input) -> None:
        return user_input == "this passes"

    error_message = "try again"

    validator = io_utils.create_validator(is_valid, error_message)

    document = Document("this passes")
    assert validator.validate(document) is None

    document = Document("this doesn't")
    with pytest.raises(ValidationError) as e:
        validator.validate(document)

    assert e.value.message == error_message
