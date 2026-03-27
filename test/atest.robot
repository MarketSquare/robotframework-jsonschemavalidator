*** Settings ***
Documentation  test
Library  JsonValidator  schema=test/testdata/schema.json  fail_on_error=True  AS  jv


*** Test Cases ***
Validate bad json file 
    [Documentation]  testing with json file
    Run Keyword And Expect Error   STARTS: SchemaValidationError  jv.Validate Json  data=test/testdata/test.json  name=tc1

Validate bad json dict
    [Documentation]  testing with dict
    VAR  &{jsondata}  name=${1}  px=${33.44}  
    Run Keyword And Expect Error   STARTS: SchemaValidationError:  jv.Validate Json  data=${jsondata}  name=tc2


Validate multiple bad json
    [Documentation]  testing with dict
    VAR  &{jsondata}  name=${1}  price=${33}
    VAR  @{jsonlist}  test/testdata/test.json  ${jsondata}
    Run Keyword And Expect Error  STARTS: SchemaValidationError:  jv.Validate Multiple Json  ${jsonlist}  prefix=TC3


Validate good json dict
    [Documentation]  testing with dict
    VAR  &{jsondata}  name=test  price=${33.44}  
     jv.Validate Json  data=${jsondata}  name="test dict"

Reset Schema Demo
    jv.Reset Schema
    # Next call will fail because no schema is loaded
    Run Keyword And Expect Error  STARTS: SchemaNotLoadedError:    jv.Validate Json    {"id": 1}

# Reset Validation Errors
#     jv.Validate Json   {"invalid": "value"}
#     Should be empty  ${jv.error_list}  # Shows collected errors
#     Reset Errors
#     Should Be Empty    ${error_list}