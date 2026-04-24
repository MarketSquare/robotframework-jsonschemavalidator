import jsonschema
import json
from robot.api.deco import keyword, not_keyword, library
import robot.api.logger as logger
from . import validation_errors
from typing import Any, Optional
import tabulate

@library
class JsonSchemaValidator:
    """
    *JSON Schema Validator*
    -----------------
    A lightweight JSON validation helper intended for use in Robot Framework test suites.

    `JsonSchemaValidator` can load a JSON Schema from a dict or a path-like string and
    validate JSON payloads, collecting errors or raising them immediately based on
    configuration.
    """

    ROBOT_LIBRARY_SCOPE = "TEST"

    @not_keyword
    def __init__(
        self, schema: Optional[str | dict[str, Any]] = None, fail_on_error: bool = True
    ) -> None:
        """
        Initialize the JSON validator and optionally load a schema.

        Parameters
        ----------
        | schema : str or dict, optional 
        |    Either a path to a JSON Schema file (``.json``) or an in-memory JSON
        |    Schema dictionary. If ``None``, no schema is loaded at construction time
        |    and method `load_new_schema` must be called before validation.
        |
        | fail_on_error : bool, optional
        |    When ``True`` (default), validation errors raise an exception immediately.
        |    When ``False``, validation issues are appended to attribute `error_list` for
        |    later inspection.

        Raises
        ------
        | ValueError
        |    If the provided ``schema`` argument is neither a string nor a dictionary,
        |    or if schema loading fails depending on method `load_new_schema`.
        |
        | FileNotFoundError
        |    If a string path is provided but the file cannot be found.

        How To Import
        -------
        | ***** Settings *****
        | Library     JsonSchemaValidator     schema=${CURDIR}/schemas/order_schema.json     fail_on_error=${True}
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

        This method accepts either:

        - a dictionary containing the JSON Schema, or
        - a string path (e.g., ``.json`` file) pointing to a JSON Schema on disk.

        The method first attempts to interpret ``schema`` as a ready-to-use dictionary
        and compile it via the internal validator setup. 
        
        If schema compilation fails due to a ``jsonschema.exceptions.SchemaError``, the method attempts to treat
        the argument as a filesystem path, read the JSON file, and compile the resulting
        schema. On success, attribute `schema_loaded` is set to ``True``.

        Parameters
        ----------
        | schema : str or dict
        |    A JSON Schema dictionary or a path (string) to a JSON Schema file.

        Raises
        ------
        | FileNotFoundError
        |    If a path is provided but the file does not exist.
        |
        | PermissionError
        |    If the schema file cannot be read due to insufficient permissions.
        |
        | json.JSONDecodeError
        |    If the schema file contains invalid JSON.
        |
        | jsonschema.exceptions.SchemaError
        |    If the schema (dictionary or loaded file content) is structurally invalid
        |    according to the JSON Schema specification.
        |
        | TypeError
        |    If ``schema`` is neither a string nor a mapping, depending on the behavior
        |    of ``_set_schema_validator`` and ``_read_json``.
        |
        | ValueError
        |    If the schema content cannot be interpreted as a valid JSON Schema by the
        |    underlying validator.

        Side Effects
        ------------
        - Sets attribute `schema_loaded` to ``True`` on success.
        - May clear or reinitialize internal error state (e.g., attribute `error_list`), depending on how ``_set_schema_validator`` is implemented.

        Examples
        --------
        | ***** Test Cases *****
        | Load Schema From File
        |    Load New Schema    ${CURDIR}/schemas/order.schema.json
        |    # Now validate payloads with the loaded schema

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

        This keyword validates a JSON payload that may be provided either as a Python
        dictionary or as a filesystem path to a JSON file. The payload is validated
        against the currently loaded JSON Schema. Any validation errors encountered are
        collected via method `_set_errors`.

        When ``fail_on_error`` is ``True`` (default), this keyword logs the errors and
        raises `SchemaValidationError` if any validation issues occur. When
        ``False``, validation errors are stored in attribute `error_list` without interrupting
        execution.

        Parameters
        ----------
        | data : dict or str
        |    A dictionary representing a JSON document, or a string path pointing to a
        |    JSON file on disk.
        |
        | name : str, optional
        |     Optional label identifying the document under validation. When ``data`` is
        |    a filepath and ``name`` is ``None``, the filepath itself is used as the
        |    source identifier.

        Raises
        ------
        | SchemaNotLoadedError
        |    If called before a schema has been loaded.
        |
        | FileNotFoundError
        |    If ``data`` is a filepath and the referenced file does not exist.
        |
        | PermissionError
        |    If a file is provided but cannot be read due to insufficient permissions.
        |
        | json.JSONDecodeError
        |    If the provided file contains invalid JSON.
        |
        | SchemaValidationError
        |    If validation fails and ``fail_on_error`` is ``True``.

        Side Effects
        ------------
        - Appends collected validation errors (if any) to attribute `error_list`.
        - Calls method `log_errors` when ``fail_on_error`` is ``True``.

        Examples
        --------
        | ***** Test Cases *****
        | Validate A Single JSON File
        |    Validate Json    ${CURDIR}/data/order.json    name=Order Payload
                
        """
        if not self.schema_loaded:
            logger.error("No Schema Loaded To Validate Against")
            raise validation_errors.SchemaNotLoadedError("No JSONSchema loaded")
        if not isinstance(data, dict):
            if name is None:
                name = data
            data = self._read_json(data)
        errors = sorted(self.validator.evolve().iter_errors(data), key=lambda e: e.path)
        self._set_errors(errors, name)
        if self.fail_on_error:
            self._log_errors()
        if len(errors) > 0:
            raise validation_errors.SchemaValidationError("JSON does not match Schema")

    @keyword(name="Validate Multiple Json")
    def validate_multiple_json(
        self, jsondata: list[str | dict[str, Any]], prefix: str = "item"
    ) -> None:
        """
        Validate multiple JSON documents against the loaded schema.

        This keyword iterates over a list of JSON inputs, where each item may be either
        a dictionary containing JSON data or a filesystem path pointing to a JSON file.
        Each document is validated against the currently loaded JSON Schema.

        Validation errors are collected via method `_set_errors`. When ``fail_on_error``
        is ``True`` (the default), all errors encountered during processing will be
        logged, and a `SchemaValidationError` will be raised if any validation
        issues occur.
W
        Parameters
        ----------
        | jsondata : list of dict or str
        |    A list where each element is either a dictionary representing a JSON
        |    document, or a string filepath to a JSON file.
        |
        | prefix : str, optional
        |    A label prefix added to the ``source`` field for each item when storing
        |    errors. Each document receives an index-based suffix (e.g., ``"item 1"``,
        |    ``"item 2"``).

        Raises
        ------
        | SchemaNotLoadedError
        |   If no schema has been loaded prior to validation.
        |
        | FileNotFoundError
        |   If any element in ``jsondata`` is a filepath that does not exist.
        |
        | PermissionError
        |    If a file cannot be read due to insufficient permissions.
        |
        | json.JSONDecodeError
        |    If a JSON file contains invalid JSON.
        |
        | SchemaValidationError
        |    If any document does not conform to the schema and ``fail_on_error``
        |    is ``True``.

        Side Effects
        ------------
        - Appends all collected validation errors to attribute `error_list`.
        - Calls method `log_errors` when ``fail_on_error`` is ``True``.

        Examples
        --------
        | ***** Test Cases *****
        | Validate Many Documents
        |    ${items}=    Create List    data1.json    data2.json
        |    Validate Multiple Json    ${items}    prefix=Order
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
            raise validation_errors.SchemaValidationError("JSON does not match Schema")

    ### Log functions
    @keyword(name="Log Json Errors")
    def log_json_errors(self) -> None:
        """
        Log all collected validation errors in a formatted table.

        This keyword is a public wrapper around the internal method `_log_errors`
        helper. It outputs all accumulated JSON Schema validation errors stored in
        attribute `error_list` as a readable table in the Robot Framework log. The table
        includes the following columns:

        - Source: The label or filename identifying the validated document.
        - Path: Dot‑separated path to the field where the error occurred.
        - Validation: The JSON Schema rule that failed (e.g., ``type``, ``required``).
        - Error: A human‑readable description of the validation failure.

        This keyword does nothing if no errors have been collected.

        Side Effects
        ------------
        - Writes a formatted table to the Robot Framework log (via ``logger.info``).
        - May also log a summary line at ``logger.error`` level depending on the implementation of method `_log_errors`.

        Examples
        --------
        | *** Test Cases ***
        | Validate And Show Errors
        |    Validate Json    invalid.json
        """
        self._log_errors()

    @keyword(name="Log Loaded Schema")
    def log_loaded_schema(self) -> None:
        """
        Log the currently loaded JSON Schema in a pretty‑printed format.

        This keyword logs the in‑memory JSON Schema using Robot Framework’s configured
        logger (or standard logging when executed in Python). The output is formatted
        with indentation to improve readability.

        The method requires that a schema has already been loaded. If no schema is
        available, an exception is raised by method `_check_schema_loaded`.

        Raises
        ------
        | SchemaNotLoadedError
        |    If no schema has been loaded into the validator instance.

        Examples
        --------
        | ***** Test Cases *****
        | Log Current Schema
        |    Log Loaded Schema
        """
        self._check_schema_loaded()

        logger.info(json.dumps(self.validator.schema, indent=4))

    ### Reset functions

    @keyword(name="Reset Errors")
    def reset_errors(self) -> None:
        """
        Clear all stored validation errors.

        This keyword resets the internal error buffer by replacing
        attribute `error_list` with an empty list. It is typically used before running a
        new validation cycle when collecting errors (i.e., when ``fail_on_error`` is
        set to ``False``).

        Side Effects
        ------------
        - Empties attribute `error_list`.
        """
        self.error_list = []

    @keyword(name="Reset Schema")
    def reset_schema(self) -> None:
        """
        Clear the currently loaded JSON Schema and reset validator state.

        This keyword removes the active validator instance and marks the schema as not
        loaded. After calling this keyword, any operation that requires a loaded schema
        (such as validation or schema logging) will raise
        `SchemaNotLoadedError` until a new schema is loaded via
        method `load_new_schema`.

        Side Effects
        ------------
        - Sets attribute `schema_loaded` to ``False``.
        - Deletes the ``validator`` attribute from the instance.

        Examples
        --------
        | ***** Test Cases *****
        | Reset Schema Demo
        |    Reset Schema
        |    # Next call will fail because no schema is loaded
        |    Run Keyword And Expect Error    STARTS: SchemaNotLoadedError    Validate Json    {"id": 1}
        """
        self.schema_loaded = False
        if hasattr(self, "validator"):
            del self.validator

    ### helper functions

    @not_keyword
    def _set_schema_validator(self, schema: dict[str, Any]) -> None:
        """
        Create and configure a JSON Schema validator instance.

        This internal helper selects the appropriate validator class based on the
        ``$schema`` field in the provided schema, verifies that the schema is valid
        according to the JSON Schema specification, and initializes the validator
        instance used for subsequent payload validation.

        The selected validator is stored on ``self.validator`` for later use.

        Parameters
        ----------
        schema : dict
            A JSON Schema as a Python dictionary. This must already be parsed JSON,
            not a filesystem path.

        Raises
        ------
        jsonschema.exceptions.SchemaError
            If the provided schema is invalid or fails structural validation.
        TypeError
            If ``schema`` is not a dictionary-like object that can be interpreted
            as a JSON Schema.
        ValueError
            If the validator cannot be constructed for the provided schema.

        Side Effects
        ------------
        * Assigns a validator instance to ``self.validator``.
        * May clear or overwrite any previously set validator.
        """
        Validator = jsonschema.validators.validator_for(schema)
        Validator.check_schema(schema)
        self.validator = Validator(schema)

    @not_keyword
    def _read_json(self, file: str) -> dict[str, Any]:
        """
        Read and parse a JSON file from disk.

        This internal helper opens the file at the given path and loads its contents as
        JSON. It is used primarily by method `load_new_schema` when a schema is supplied
        as a filesystem path rather than a dictionary.

        Parameters
        ----------
        file : str
            Path to a JSON file on disk.

        Returns
        -------
        dict
            A dictionary containing the parsed JSON data.

        Raises
        ------
        FileNotFoundError
            If the specified file path does not exist.
        PermissionError
            If the file cannot be opened due to insufficient permissions.
        json.JSONDecodeError
            If the file exists but does not contain valid JSON.
        OSError
            For other I/O‑related errors encountered while opening the file.

        Examples
        --------
        .. code-block:: robotframework

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

        This internal helper normalizes and appends validation errors produced by the
        active JSON Schema validator to attribute `error_list`. Each stored entry is a
        four‑element list with the following structure::

            [source, path, validator, message]

        Where:

        * ``source`` — A string indicating the origin of the validated document
        (e.g., a filename or logical name). An empty string is stored if no source
        is provided.
        * ``path`` — A dot‑separated string representing the location of the failing
        field within the JSON document (e.g., ``"items.0.id"``).
        * ``validator`` — The JSON Schema validator keyword that failed (e.g.,
        ``"type"``, ``"required"``).
        * ``message`` — A human‑readable description of the validation failure.

        Parameters
        ----------
        errors : iterable
            An iterable of validation error objects. Typically instances of
            ``jsonschema.exceptions.ValidationError`` or compatible objects with the
            attributes:

            * ``path`` — deque or path-like sequence of keys/indices
            * ``validator`` — the schema rule that failed
            * ``message`` — textual explanation of the failure
        source : str, optional
            Optional descriptor of the document under test (e.g., a filename or
            logical alias). If ``None``, an empty string is stored.

        Side Effects
        ------------
        * Appends entries to attribute `error_list`. Existing entries are preserved.

        Notes
        -----
        * ``e.path`` may contain integers (e.g., array indices). To avoid
        ``TypeError`` when joining path components, elements are cast to ``str``.
        * If you intend to clear previous errors before collecting new ones, this
        must be done by the caller (e.g., at the beginning of a validation operation).

        """
        for e in errors:
            self.error_list.append(
                [source or "", ".".join(map(str, e.path)), e.validator, e.message]
            )

    @not_keyword
    def _log_errors(self) -> None:
        """
        Log all collected validation errors in a formatted table.

        This keyword outputs the contents of attribute `error_list` as a readable table in
        the test log, using ``tabulate`` for formatted rendering. Each row in the table
        represents a single validation error and includes:

        * **Source** – The name, path, or label of the validated document.
        * **Path** – Dot‑separated location within the JSON payload where the validation
        failure occurred.
        * **Validation** – The JSON Schema validator that failed (e.g., ``type``,
        ``required``).
        * **Error** – The human‑readable validation message.

        This keyword does nothing if no errors have been collected.

        Side Effects
        ------------
        * Writes a formatted table of errors to the Robot Framework log (via
        ``logger.error``).

        Examples
        --------
        .. code-block:: robotframework

            *** Test Cases ***
            Show Validation Errors
                Validate Json    invalid.json
                Log Errors

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
        """
        Ensure that a JSON Schema has been loaded before validation.

        This internal guard method is used by operations that require an active
        schema (for example, validation or schema logging). If no schema has been
        loaded, an error is logged and a `SchemaNotLoadedError` is raised.

        Raises
        ------
        SchemaNotLoadedError
            If no schema has been loaded into the validator instance.

        Side Effects
        ------------
        * Logs an error message via the module logger when no schema is loaded.
        """
        if not self.schema_loaded:
            logger.error("No Schema Loaded To Validate Against")
            raise validation_errors.SchemaNotLoadedError("No JSONSchema loaded")
