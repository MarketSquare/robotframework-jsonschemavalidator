*** Settings ***
Documentation  test
Library  JsonValidator  schema=test/testdata/schema.json  fail_on_error=True


*** Test Cases ***
Validate bad json file 
    [Documentation]  testing with json file
    Run Keyword And Expect Error   STARTS: SchemaValidationError  JsonValidator.Validate Json  data=test/testdata/test.json  name=tc1

Validate bad json dict
    [Documentation]  testing with dict
    VAR  &{jsondata}  name=${1}  px=${33.44}  
    Run Keyword And Expect Error   STARTS: SchemaValidationError:  JsonValidator.Validate Json  data=${jsondata}  name=tc2


Validate multiple bad json
    [Documentation]  testing with dict
    VAR  &{jsondata}  name=${1}  price=${33}
    VAR  @{jsonlist}  test/testdata/test.json  ${jsondata}
    Run Keyword And Expect Error  STARTS: SchemaValidationError:  JsonValidator.Validate Multiple Json  ${jsonlist}  prefix=TC3


Validate good json dict
    [Documentation]  testing with dict
    VAR  &{jsondata}  name=test  price=${33.44}  
    JsonValidator.Validate Json  data=${jsondata}  name="test dict"


Reset Schema Demo
    [Documentation]  Test to verify schema reset
    Reset Schema
    # Next call will fail because no schema is loaded
    Run Keyword And Expect Error    STARTS: SchemaNotLoadedError    JsonValidator.Validate Json    {"id": 1}