# 📘 robotframework-jsonvalidator

A lightweight and extensible JSON Schema validation library for use in **Robot Framework** test suites.  
Designed for clarity, reliability, and maintainability, it provides meaningful diagnostics when validating one or multiple JSON documents.

---

## 🚀 Overview

`robotframework-jsonschemavalidator` enables automated test suites to validate JSON payloads using standard JSON Schemas.  
It offers configurable validation behavior and clean logging to support both small and large‑scale test automation.

This library focuses on:

- Clear JSON structure validation  
- Helpful, readable error reporting  
- Easy use within Robot Framework  
- Flexibility for local development and CI/CD environments  

---

## ✨ Features

- **Schema-based validation** using the well‑known `jsonschema` engine  
- Load schemas from **file paths** or **in‑memory dictionaries**  
- Validate **single** or **multiple** JSON documents  
- Choose between:
  - **Fail‑fast mode** for immediate errors  
  - **Collect‑all mode** for batch reporting per test
- Error reporting includes:
  - Source document identifier  
  - JSON path to the error location  
  - Failing schema keyword  
  - Human‑readable explanation  
- Designed for seamless integration with:
  - **Robot Framework**
  - **CI/CD**

---

## 📦 Installation

### Using uv (recommended)

```bash
uv add robotframework-jsonschemavalidator
```

### Using poetry

```bash
poetry add robotframework-jsonschemavalidator
```

### Using pip

```bash
pip install robotframework-jsonschemavalidator
```

This makes the library available to Robot Framework as:

```robot
*** Settings ***
Library    JsonSchemaValidator
```

---

## 🧱 Project Structure

```txt
robotframework-jsonschemavalidator/
├─ pyproject.toml
├─ src/
│   └─ JsonSchemaValidator/
│       ├─ __init__.py
│       ├─ JsonSchemaValidator.py   # Core implementation
│       └─ errors.py
└─ tests/
    └─ atest.robot
```


## 🧪 Testing & Development

### Running Robot Tests

```bash
uv run robot tests/
```

## 🤝 Contributing

Contributions are encouraged and appreciated.  
To contribute:

1. Fork the repository  
2. Create a feature branch  
3. Commit changes with meaningful messages  
4. Submit a pull request  

For major changes, please open an issue to discuss before starting work.

### Contributing Guidelines

- Maintain consistent naming for keywords  
- Keep documentation up to date with new features  
- Include tests for new functionality  
- Follow existing styles for logging and error reporting  

Pull requests and issue reports are welcome!

---

## 📄 License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE).

---

## Author

[Mickel Jacobs](https://www.linkedin.com/in/mickel-j/)