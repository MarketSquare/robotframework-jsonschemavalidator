*** Settings ***
Documentation  test
Library  JsonValidator.py  schema=schema.json  errors_on_validation=False  AS  jv
Suite Teardown  jv.Log Errors

*** Variables ***


*** Test Cases ***
Validate bad json file 
    [Documentation]  testing with json file
    Run Keyword And Expect Error   STARTS: SchemaValidationError  jv.Validate Json  data=test.json  name=tc1

Validate bad json dict
    [Documentation]  testing with dict
    VAR  &{jsondata}  name=${1}  px=${33.44}  
    Run Keyword And Expect Error   STARTS: SchemaValidationError:  jv.Validate Json  data=${jsondata}  name=tc2


Validate multiple bad json
    [Documentation]  testing with dict
    VAR  &{jsondata}  name=${1}  price=${33}
    VAR  @{jsonlist}  test.json  ${jsondata}
    Run Keyword And Expect Error  STARTS: SchemaValidationError:  jv.Validate Multiple Json  ${jsonlist}  prefix=TC3


Validate good json dict
    [Documentation]  testing with dict
    VAR  &{jsondata}  name=test  price=${33.44}  
     jv.Validate Json  data=${jsondata}  name="test dict"
