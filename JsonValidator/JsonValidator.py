"""
json_validator.py
-----------------

A lightweight JSON validation helper intended for use both in Python and
Robot Framework test suites.

`JsonValidator` can load a JSON Schema from a dict or a path-like string and
validate JSON payloads, collecting errors or raising them immediately based on
configuration.

Typical usage:

    validator = JsonValidator(schema="schemas/order.schema.json")
    validator.validate_json({"id": 1, "items": []})

Robot Framework usage:

    *** Settings ***
    Library     JsonValidator     schema=${CURDIR}/schemas/order.schema.json    fail_on_error=${True}

    *** Test Cases ***
    Validate Order Json
        VAR  &{payload}=     id=1  items=@{EMPTY}
        Validate Json    ${payload}
"""

import jsonschema
import json
from robot.api.deco import keyword, not_keyword
import robot.api.logger as logger
from .errors import SchemaNotLoadedError, SchemaValidationError
from typing import Any
import tabulate


class JsonValidator:
    """
    Validate JSON documents against a JSON Schema.

    This library is designed to be used both in Python and in Robot Framework.
    When used in Robot Framework, the scope is limited to a single test due to
    `ROBOT_LIBRARY_SCOPE = 'TEST'`, meaning a fresh instance is created for
    each test case (no cross-test state leakage).

    Attributes:
        ROBOT_LIBRARY_SCOPE (str): Robot Framework scope; set to ``'TEST'``
            so each test gets a clean instance.
        error_list (list[str]): Collected validation error messages from the
            most recent operation(s). This list is cleared when loading a
            new schema or before validation runs, depending on your internal
            design choices.
        fail_on_error (bool): If ``True``, validation failures will be
            raised immediately as exceptions. If ``False``, failures are
            accumulated in ``error_list`` and can be retrieved after
            validation.
        schema_loaded (bool): Flag indicating whether a schema has been
            successfully loaded.

    Examples:
        Load schema from dict and validate:

            >>> schema = {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]}
            >>> v = JsonValidator(schema=schema, fail_on_error=True)
            >>> v.validate_json({"id": 123})  # No exception

        Load schema from file path and collect errors instead of raising:

            >>> v = JsonValidator(schema="schemas/order.schema.json", fail_on_error=False)
            >>> v.validate_json({"id": "not-an-integer"})
            >>> v.error_list  # doctest: +ELLIPSIS
            ['... must be integer ...']
    """

    ROBOT_LIBRARY_SCOPE = "TEST"

    @not_keyword
    def __init__(
        self, schema: str | dict[str, Any] = None, fail_on_error: bool = True
    ) -> None:
        """
        Initialize the JSON validator and optionally load a schema.

        Args:
            schema: Either a path to a JSON Schema file (``.json``) or an
                in-memory JSON Schema dictionary. If ``None``, no schema is
                loaded at construction time, and you must call
                :meth:`load_new_schema` before validation.
            fail_on_error: When ``True`` (default), validation errors
                raise an exception immediately. When ``False``, validation
                issues are appended to :attr:`error_list` for later inspection.

        Attributes Initialized:
            error_list: An empty list used to collect validation error messages.
            fail_on_error: Mirrors the passed flag to control error
                handling behavior.
            schema_loaded: Indicates whether a schema is currently loaded.

        Raises:
            ValueError: If the provided ``schema`` argument is neither a string
                nor a dictionary (when provided), or if loading the schema
                fails (depending on your :meth:`load_new_schema` implementation).
            FileNotFoundError: If a string path is provided but the file cannot
                be found (depending on :meth:`load_new_schema`).

        Example:
            >>> # Construct without a schema, then load one later
            >>> v = JsonValidator(fail_on_error=False)
            >>> v.load_new_schema({"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]})
            >>> v.validate({"name": "Alice"})
            >>> v.error_list
            []
        """

        self.error_list = []
        self.fail_on_error = fail_on_error
        self.schema_loaded = False

        if schema is not None:
            self.load_new_schema(schema=schema)

    @keyword(name="Load New Schema")
    def load_new_schema(self, schema: str | dict[str, Any]) -> None:
        """
        Load and set a new JSON Schema for validation.

        Accepts either:
        - a **dictionary** containing the JSON Schema, or
        - a **string path** (e.g., ``.json`` file) pointing to a JSON Schema on disk.

        This method first tries to treat ``schema`` as a ready-to-use schema object
        and compile it via the internal validator setup. If that fails due to a
        schema compilation issue (`jsonschema.exceptions.SchemaError`), it will
        attempt to **read** the argument as a filesystem path, parse the JSON, and
        compile the resulting schema. On success, :attr:`schema_loaded` is set to
        ``True``.

        Args:
            schema: A JSON Schema dictionary or a path (string) to a JSON Schema file.

        Raises:
            FileNotFoundError: If a path is provided but the file does not exist.
            PermissionError: If the schema file is not readable due to permissions.
            json.JSONDecodeError: If a file is provided and contains invalid JSON.
            jsonschema.exceptions.SchemaError: If the schema (dict or file content)
                is structurally invalid per the JSON Schema specification.
            TypeError: If ``schema`` is neither a string nor a mapping (depending on
                the behavior of ``_set_schema_validator`` / ``_read_json``).
            ValueError: If the schema content cannot be interpreted as a valid JSON
                Schema by the underlying validator.

        Side Effects:
            - Sets :attr:`schema_loaded` to ``True`` on success.
            - May clear or reinitialize internal error state as per implementation
            (e.g., :attr:`error_list`), depending on how ``_set_schema_validator``
            is designed.

        Examples:
            Load from a dict (Python):
                >>> schema_dict = {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]}
                >>> v = JsonValidator(fail_on_error=True)
                >>> v.load_new_schema(schema_dict)
                >>> v.schema_loaded
                True

            Load from a file path (Python):
                >>> v = JsonValidator()
                >>> v.load_new_schema("schemas/order.schema.json")
                >>> v.schema_loaded
                True

        Robot Framework (library imported with no schema, then load):
            *** Test Cases ***
            Load Schema From File
                Load New Schema    ${CURDIR}/schemas/order.schema.json
                # Now validate payloads with the loaded schema
        """
        try:
            self._set_schema_validator(schema)
        except jsonschema.exceptions.SchemaError:
            data = self._read_json(schema)
            self._set_schema_validator(data)
        self.schema_loaded = True

    ### Validation Keywords

    @keyword(name="Validate Json")
    def validate_json(self, data: str | dict[str, Any], name=None):
        """
        Validate a single JSON document against the loaded schema.

        This keyword validates a single JSON payload which may be passed either
        as a dictionary or as a filesystem path to a JSON file. The document is
        validated against the currently loaded JSON Schema. Any validation errors
        encountered are collected via :meth:`_set_errors`.

        When ``fail_on_error`` is ``True`` (default), this keyword logs
        the errors and raises :class:`SchemaValidationError` if any issues are
        found. When ``False``, errors are merely stored in :attr:`error_list`.

        Args:
            data:
                Either a dictionary representing a JSON document, or a string
                path pointing to a JSON file on disk.
            name:
                Optional label identifying the document under validation. When
                ``data`` is a filepath and ``name`` is ``None``, the filepath
                itself is used as the source identifier.

        Raises:
            SchemaNotLoadedError:
                If called before a schema is loaded.
            FileNotFoundError:
                If ``data`` is a filepath and the file does not exist.
            PermissionError:
                If the file cannot be read due to permissions.
            json.JSONDecodeError:
                If the file contains invalid JSON.
            SchemaValidationError:
                If validation fails and ``fail_on_error`` is ``True``.

        Side Effects:
            - Appends collected errors (if any) to :attr:`error_list`.
            - Calls :meth:`log_errors` when ``fail_on_error`` is ``True``.

        Examples:
            Robot Framework:
                *** Test Cases ***
                Validate A Single JSON File
                    Validate Json    ${CURDIR}/data/order.json    name=Order Payload

            Python:
                >>> schema = {"type": "object", "properties": {"id": {"type": "integer"}}}
                >>> v = JsonValidator(schema=schema)
                >>> v.validate_json({"id": 1})   # passes
                >>> v.validate_json({"id": "x"}) # raises SchemaValidationError
        """
        if not self.schema_loaded:
            logger.error("No Schema Loaded To Validate Against")
            raise SchemaNotLoadedError("No JSONSchema loaded")
        if not isinstance(data, dict):
            if name is None:
                name = data
            data = self._read_json(data)
        errors = sorted(self.validator.evolve().iter_errors(data), key=lambda e: e.path)
        self._set_errors(errors, name)
        if self.fail_on_error:
            self._log_errors()
        if len(errors) > 0:
            raise SchemaValidationError("JSON does not match Schema")

    @keyword(name="Validate Multiple Json")
    def validate_multiple_json(
        self, jsondata: list[str | dict[str, Any]], prefix: str = "item"
    ) -> None:
        """
        Validate multiple JSON documents against the loaded schema.

        This keyword iterates over a list of JSON inputs, where each item may
        either be a dictionary containing JSON data or a filesystem path pointing
        to a JSON file. Each document is validated against the currently loaded
        JSON Schema.

        Validation errors are collected via :meth:`_set_errors`. When
        ``fail_on_error`` is ``True`` (the default), all errors encountered
        during processing will be logged and a :class:`SchemaValidationError` will
        be raised if any errors were found.

        Args:
            jsondata:
                A list where each element is either:
                    - a dictionary representing a JSON document, or
                    - a string filepath to a JSON file.
            prefix:
                A label prefix added to the ``source`` field for each item when
                storing errors. Each document receives an index-based suffix
                (e.g., ``"item 1"``, ``"item 2"``).

        Raises:
            SchemaNotLoadedError:
                If no schema has been loaded prior to validation.
            FileNotFoundError:
                If any element is a filepath and the file does not exist.
            PermissionError:
                If a file cannot be read due to permissions.
            json.JSONDecodeError:
                If a JSON file contains invalid JSON.
            SchemaValidationError:
                If any document does not conform to the schema and
                ``fail_on_error`` is ``True``.

        Side Effects:
            - Errors from all documents are appended to :attr:`error_list`.
            - Calls :meth:`log_errors` when ``fail_on_error`` is ``True``.

        Examples:
            Robot Framework:
                *** Test Cases ***
                Validate Many Documents
                    ${items}=    Create List    data1.json    data2.json
                    Validate Multiple Json    ${items}    prefix=Order

            Python:
                >>> items = [{"id": 1}, {"id": "wrong-type"}]
                >>> v = JsonValidator(schema={"type": "object"})
                >>> v.validate_multiple_json(items)
                Traceback (most recent call last):
                    ...
                SchemaValidationError: JSON does not match Schema
        """
        self._check_schema_loaded()

        any_errors = False

        for i, file in enumerate(jsondata):
            if not isinstance(file, dict):
                file = self._read_json(file)

            errors = sorted(
                self.validator.evolve().iter_errors(file), key=lambda e: e.path
            )

            if errors:
                any_errors = True

            self._set_errors(errors, source=f"{prefix} {i+1}")

        if self.fail_on_error:
            self._log_errors()

        if any_errors:
            raise SchemaValidationError("JSON does not match Schema")

    ### Log functions
    @keyword(name="Log Json Errors")
    def log_json_errors(self) -> None:
        """
        Log all collected validation errors in a formatted table.

        This keyword is a public wrapper around the internal :meth:`_log_errors`
        helper. It outputs all accumulated JSON Schema validation errors stored in
        :attr:`error_list` as a readable table in the Robot Framework log. The table
        includes the following columns:

            - **Source**: The label or filename identifying the validated document.
            - **Path**: Dot‑separated path to the field where the error occurred.
            - **Validation**: The JSON Schema rule that failed (e.g., ``type``,
            ``required``).
            - **Error**: A human‑readable description of the validation failure.

        This keyword does nothing if no errors have been collected.

        Side Effects:
            - Writes a formatted table to the Robot Framework log (via ``logger.info``).
            - May also log a summary line at ``logger.error`` level depending on the
            internal implementation of :meth:`_log_errors`.

        Examples:
            Robot Framework:
                *** Test Cases ***
                Validate And Show Errors
                    Validate Json    invalid.json
                    Log JSON Errors

            Python:
                >>> v = JsonValidator(errors_on_validation=False)
                >>> v.error_list = [
                ...     ["payload.json", "items.0.id", "type", "must be integer"]
                ... ]
                >>> v.log_json_errors()   # Logs the formatted table
        """
        self._log_errors()

    @keyword(name="Log Loaded Schema")
    def log_loaded_schema(self) -> None:
        """
        Log the currently loaded JSON Schema in a pretty‑printed format.

        This keyword logs the in-memory JSON Schema using Robot Framework’s
        configured logger (or standard logging when executed in Python). The
        log output is formatted with indentation to improve readability.

        The method requires that a schema has already been loaded. If no schema
        is available, an exception is raised by :meth:`_check_schema_loaded`.

        Raises:
            RuntimeError: If no schema has been loaded prior to calling
                this keyword.

        Examples:
            Robot Framework:
                *** Test Cases ***
                Log Current Schema
                    Log Loaded Schema

            Python:
                validator = JsonValidator(schema={"type": "object"})
                validator.log_loaded_schema()
        """
        self._check_schema_loaded()

        logger.info(json.dumps(self.validator.schema, indent=4))

    ### Reset functions

    @keyword(name="Reset Errors")
    def reset_errors(self) -> None:
        """
        Clear all stored validation errors.

        This keyword resets the internal error buffer by replacing
        :attr:`error_list` with an empty list. It is typically used before running a
        new validation cycle when collecting errors (i.e., when
        ``fail_on_error`` is set to ``False``).

        Side Effects:
            - Empties :attr:`error_list`.

        Examples:
            Robot Framework:
                *** Test Cases ***
                Reset Validation Errors
                    Validate    {"invalid": "value"}
                    Log    ${error_list}    # Shows collected errors
                    Reset Errors
                    Should Be Empty    ${error_list}

            Python:
                >>> v = JsonValidator(fail_on_error=False)
                >>> v.error_list = [["payload.json", "id", "type", "must be integer"]]
                >>> v.reset_errors()
                >>> v.error_list
                []
        """
        self.error_list = []

    @keyword(name="Reset Schema")
    def reset_schema(self) -> None:
        """
        Clear the currently loaded JSON Schema and reset validator state.

        This keyword removes the active validator instance and marks the schema as
        not loaded. After calling this, any operation requiring a loaded schema
        (such as validation or schema logging) will raise
        :class:`SchemaNotLoadedError` until a new schema is loaded via
        :meth:`load_new_schema`.

        Side Effects:
            - Sets :attr:`schema_loaded` to ``False``.
            - Deletes the ``validator`` attribute from the instance.

        Raises:
            AttributeError:
                If ``self.validator`` does not exist at the time of deletion.

        Examples:
            Robot Framework:
                *** Test Cases ***
                Reset Schema Demo
                    Reset Schema
                    # Next call will fail because no schema is loaded
                    Run Keyword And Expect Error    *SchemaNotLoadedError*    Validate    {"id": 1}

            Python:
                >>> v = JsonValidator(schema={"type": "object"})
                >>> v.reset_schema()
                >>> v.schema_loaded
                False
                >>> hasattr(v, "validator")
                False
        """
        self.schema_loaded = False
        if hasattr(self, "validator"):
            del self.validator

    ### helper functions

    @not_keyword
    def _set_schema_validator(self, schema: dict[str, Any]) -> None:
        """
        Create and configure a JSON Schema validator instance.

        This internal helper chooses the appropriate validator class based on the
        `$schema` field inside the provided schema, checks that the schema is valid
        according to the JSON Schema specification, and initializes the validator
        instance used for subsequent payload validation.

        The selected validator is stored on ``self.validator`` for later use.

        Args:
            schema: A JSON Schema as a Python dictionary. This must already be
                parsed JSON—not a file path.

        Raises:
            jsonschema.exceptions.SchemaError:
                If the provided schema is invalid or fails structural validation.
            TypeError:
                If ``schema`` is not a dictionary-like object that can be
                interpreted as a JSON Schema.
            ValueError:
                If the validator cannot be constructed for the provided schema.

        Side Effects:
            - Assigns a validator instance to ``self.validator``.
            - May clear or overwrite any previously set validator.

        Examples:
            >>> from jsonschema import Draft7Validator
            >>> schema = {"type": "object", "properties": {"id": {"type": "integer"}}}
            >>> v = JsonValidator(fail_on_error=True)
            >>> v._set_schema_validator(schema)
            >>> isinstance(v.validator, Draft7Validator)
            True
        """
        Validator = jsonschema.validators.validator_for(schema)
        Validator.check_schema(schema)
        self.validator = Validator(schema)

    @not_keyword
    def _read_json(self, file: str) -> dict[str, Any]:
        """
        Read and parse a JSON file from disk.

        This internal helper opens the file at the given path and loads its
        contents as JSON. It is used primarily by :meth:`load_new_schema` when
        a schema is supplied as a filesystem path rather than a dictionary.

        Args:
            file: Path to a JSON file on disk.

        Returns:
            A dictionary containing the parsed JSON data.

        Raises:
            FileNotFoundError:
                If the specified file path does not exist.
            PermissionError:
                If the file cannot be opened due to insufficient permissions.
            json.JSONDecodeError:
                If the file exists but does not contain valid JSON.
            OSError:
                For other IO‑related errors encountered while opening the file.

        Examples:
            Python:
                >>> v = JsonValidator()
                >>> data = v._read_json("schemas/order.schema.json")
                >>> isinstance(data, dict)
                True

        Robot Framework (indirect usage via Load New Schema):
            *** Test Cases ***
            Load Schema
                Load New Schema    ${CURDIR}/schemas/order.schema.json
        """
        with open(file, "r") as jf:
            data = json.load(jf)
            return data

    @not_keyword
    def _set_errors(self, errors: list[any], source: str | None) -> None:
        """
        Store validation errors in the internal ``error_list`` buffer.

        This internal helper normalizes and appends validation errors produced by
        the active JSON Schema validator to :attr:`error_list`. Each stored entry
        is a 4‑element list with the following structure:

            [source, path, validator, message]

        Where:
            - ``source``: A string indicating the origin of the validated document
            (e.g., a filename or logical name). Empty string if not provided.
            - ``path``: A dot-separated string representing the location of the
            failing field within the JSON document (e.g., ``"items.0.id"``).
            - ``validator``: The JSON Schema validator name that failed
            (e.g., ``"type"``, ``"required"``).
            - ``message``: A human-readable error message.

        Args:
            errors:
                An iterable of validation error objects. Typically instances of
                :class:`jsonschema.exceptions.ValidationError` or compatible objects
                with the attributes:
                - ``path`` (deque/path-like of keys/indices),
                - ``validator`` (str),
                - ``message`` (str).
            source:
                Optional descriptor of the document under test (e.g., file name or
                alias). If ``None``, an empty string is stored.

        Side Effects:
            Appends entries to :attr:`error_list`. Existing entries are preserved.

        Notes:
            - ``e.path`` may contain integers (for array indices). To avoid
            ``TypeError`` when joining, elements are cast to ``str``.
            - If you intend to clear previous errors before collecting new ones,
            do so in the caller (e.g., at the beginning of ``validate``).

        Examples:
            >>> # Suppose 'errs' is a list of jsonschema ValidationError instances
            >>> v = JsonValidator(fail_on_error=False)
            >>> v.error_list = []
            >>> v._set_errors(errs, source="payload.json")
            >>> # Each entry becomes: [ "payload.json", "root.field.0", "type", "must be integer" ]
        """
        for e in errors:
            self.error_list.append(
                [source or "", ".".join(map(str, e.path)), e.validator, e.message]
            )

    @not_keyword
    def _log_errors(self) -> None:
        """
        Log all collected validation errors in a formatted table.

        This keyword outputs the contents of :attr:`error_list` as a readable
        table to the test log, using ``tabulate`` for formatted rendering. Each
        row in the table represents a single validation error, containing:

            - **Source**: The name, path, or label of the validated document.
            - **Path**: Dot‑separated location within the JSON payload where
            the validation failure occurred.
            - **Validation**: The JSON Schema validator that failed
            (e.g., ``type``, ``required``).
            - **Error**: The human‑readable validation message.

        This keyword does nothing if no errors have been collected.

        Side Effects:
            - Writes a formatted table to the Robot Framework log (via ``logger.error``).

        Examples:
            Robot Framework:
                *** Test Cases ***
                Show Validation Errors
                    Validate Json    invalid.json
                    Log Errors

            Python:
                >>> v = JsonValidator(fail_on_error=False)
                >>> v.error_list = [
                ...     ["item 1", "id", "type", "must be integer"]
                ... ]
                >>> v.log_errors()  # Logs a formatted table
        """
        if len(self.error_list) > 0:
            logger.error(
                tabulate.tabulate(
                    self.error_list,
                    tablefmt="rounded_grid",
                    headers=["Source", "Path", "Validation", "Error"],
                )
            )

    @not_keyword
    def _check_schema_loaded(self):
        """Ensure that a JSON Schema has been loaded before validation.

        This internal guard method is used by operations that require an active
        schema (e.g., validation, schema logging). If no schema has been loaded,
        an error is logged and a :class:`SchemaNotLoadedError` is raised.

        Raises:
            SchemaNotLoadedError:
                If no schema has been loaded into the validator instance.

        Side Effects:
            - Logs an error message via the module logger when no schema is loaded.

        Examples:
            >>> v = JsonValidator()
            >>> v.schema_loaded
            False
            >>> v._check_schema_loaded()
            Traceback (most recent call last):
                ...
            SchemaNotLoadedError: No JSONSchema loaded

            >>> v = JsonValidator(schema={"type": "object"})
            >>> v._check_schema_loaded()   # No exception
        """
        if not self.schema_loaded:
            logger.error("No Schema Loaded To Validate Against")
            raise SchemaNotLoadedError("No JSONSchema loaded")
