import jsonschema
import json
from robot.api.deco import keyword, not_keyword
import robot.api.logger as logger
from .errors import SchemaNotLoadedError, SchemaValidationError
from typing import Any
import tabulate


class JsonValidator:

    ROBOT_LIBRARY_SCOPE = 'TEST' 

    def __init__(self, schema:str|dict[str,Any]=None, errors_on_validation: bool = True) -> None:
        """
        Docstring for __init__
        
        :param schema: Description
        :type schema: str | dict[str, Any]
        :param errors_on_validation: Description
        :type errors_on_validation: bool
        """

        self.error_list = []
        self.errors_on_validation = errors_on_validation
        self.schema_loaded = False

        if schema is not None:
            self.load_new_schema(schema=schema)

    @keyword
    def load_new_schema(self, schema:str|dict[str,Any]) -> None:
        """
        Docstring for load_new_schema
        
        :param self: Description
        :param schema: Description
        :type schema: str | dict[str, Any]
        """
        try:
            self._set_schema_validator(schema)
        except jsonschema.exceptions.SchemaError:
            data = self._read_json(schema)
            self._set_schema_validator(data)
        self.schema_loaded = True



    ### Validation Keywords

    @keyword
    def validate_json(self,  data:str|dict[str, Any], name=None):
        """
        Docstring for validate_json
        
        :param self: Description
        :param data: Description
        :type data: str | dict[str, Any]
        :param name: Description
        """
        if not self.schema_loaded:
            logger.error("No Schema Loaded To Validate Against")
            raise SchemaNotLoadedError("No JSONSchema loaded")
        if not isinstance(data, dict):
            if name is None:
                name = data
            data = self._read_json(data)
        errors = sorted(self.validator.evolve().iter_errors(data), key=lambda e:e.path)        
        self._set_errors(errors, name)
        if self.errors_on_validation:
            self.log_errors()
        if len(errors) > 0:
            raise SchemaValidationError("JSON does not match Schema")

    @keyword
    def validate_multiple_json(self, jsondata: list[str|dict[str, Any]], prefix:str="item") -> None:
        self._check_schema_loaded()
        
        for i, file in enumerate(jsondata):
            if not isinstance(file, dict):
                file = self._read_json(file)
            errors = sorted(self.validator.evolve().iter_errors(file), key=lambda e:e.path)        
            self._set_errors(errors, source=f"{prefix} {i+1}")
        if self.errors_on_validation:
            self.log_errors()
        if len(errors) > 0:
            raise SchemaValidationError("JSON does not match Schema")


    ### Log functions

    @keyword
    def log_errors(self) -> None:
        """
        Log a table of found errors to the test log file
        """
        if len(self.error_list) > 0:
            logger.error("Found errors in JSON")

            logger.info(tabulate.tabulate(
                self.error_list,
                tablefmt="rounded_grid",
                headers=["Source","Path", "Validation", "Error"]
            ))

    @keyword
    def log_loaded_schema(self) -> None:
        """
        Docstring for log_loaded_schema
        
        :param self: Description
        """
        self._check_schema_loaded()

        logger.info(json.dumps(self.validator.schema, indent=4))


    ### Reset functions

    @keyword
    def reset_errors(self) -> None:
        """
        Clear the logged errors
        """
        self.error_list = []

    @keyword
    def reset_schema(self) -> None:
        """
        Clear the loaded JSONSchema
        """
        self.schema_loaded = False
        del self.validator


    ### helper functions

    @not_keyword
    def _set_schema_validator(self, schema: dict[str, Any]) -> None:
        """
        Docstring for _set_schemma_validator
        
        :param self: Description
        :param schema: Description
        :type schema: dict[str, Any]
        """
        Validator = jsonschema.validators.validator_for(schema)
        Validator.check_schema(schema)
        self.validator = Validator(schema)

    @not_keyword
    def _read_json(self, file:str) -> dict[str, Any]:
        """
        Docstring for _read_json
        
        :param self: Description
        :param file: Description
        :type file: str
        :return: Description
        :rtype: dict[str, Any]
        """
        with open(file, "r") as jf:
            data = json.load(jf)
            return data

    @not_keyword
    def _set_errors(self, errors:list[any], source:str|None) -> None:
        """
        Private function for storing found errors in a list. 
        
        :param errors: List of found errors in the document
        :type errors: list[any]
        :param source: Specified name or file name of the document under test
        :type source: str | None
        """
        for e in errors:
            self.error_list.append([
                source or "",
                ".".join(e.path),
                e.validator,
                e.message
            ])

    @not_keyword
    def _check_schema_loaded(self):
        if not self.schema_loaded:
            logger.error("No Schema Loaded To Validate Against")
            raise SchemaNotLoadedError("No JSONSchema loaded")