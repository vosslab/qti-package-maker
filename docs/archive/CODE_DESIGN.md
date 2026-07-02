# **QTI Package Maker - Code Design Guide**
_A deep dive into the architecture and philosophy behind the QTI Package Maker_

---

## **Introduction**
This document provides a **high-level overview** of how the QTI Package Maker is structured, including how it **reads**, **stores**, and **writes** assessment item data across multiple formats.

The system is designed to be:
- **Extensible** - New formats can be added easily.
- **Modular** - Components are independent but work together.
- **Format-agnostic** - The internal structure remains the same, regardless of file format.

## **Designed Usage**

``` python3
# import the main interface
from qti_package_maker import package_interface
# create a interface class instance
pmaker = package_interface.QTIPackageInterface()
# some member functions
pmaker.show_available_engines()
# read function opens engine qti21 and reads that type of input file
pmaker.read_package('input_blackboard_qti21.zip', engine_name='qti21', verbose=True)
# assessment_item item_type classes are stored in an item_bank.ItemBank
# read 99 questions from file
pmaker.summarize_item_bank()
pmaker.print_item_bank_histogram()
#MC 45 questions
#MATCH 44 questions
pmaker.write_package('output_canvas_qti12.zip', engine_name='qti12', verbose=True)
#wrote 99 questions
```

## **Architectural Overview**

### **Core Components**
The project consists of **four main layers**:

| Layer | Purpose |
|--------|---------|
| `QTIPackageInterface` | The main interface for reading/writing assessment items, orchestrating different engines. |
| `ItemBank` | Stores assessment items in a unified internal format, decoupled from file formats. |
| `Assessment Item Classes` | Separate classes for each assessment item type, all inheriting from a base `AssessmentItem` class (e.g., MA, MC, MATCH). These validate and store assessment items in a format that avoids if-else logic, clearly defining each type. They can be built from a read engine and passed to a write engine. |
| `(Read and Write) Engines` | Format-specific modules that convert between assessment item objects and external file formats (e.g., QTI 1.2, QTI 2.1, human-readable). |

```
qti_package_maker/
|-- engines/
|   |-- qti_v1_2/
|   |   |-- engine_class.py
|   |   |-- add_item.py
|   |-- qti_v2_1/
|   |   |-- engine_class.py
|   |   |-- add_item.py
|   |-- human_readable/
|   |   |-- engine_class.py
|-- common/
|   |-- base_package_maker.py
|   |-- string_functions.py
|-- package_interface.py
```

---

### **1) Master Controller: `QTIPackageInterface`**
This class is the **main entry point** for interacting with the package. It:
- **Reads assessment items** from different formats (QTI 1.2, QTI 2.1, human-readable, etc.).
- **Stores them centrally** in an `ItemBank`.
- **Writes them back** to different formats.

```python
class QTIPackageInterface:
    def __init__(self):
        self.item_bank = ItemBank()
        self.engines = {
            "qti21": QTIv2Engine,
            "qti12": QTIv1Engine,
            "human": HumanReadable,
        }

    def read(self, input_file, format, verbose=False):
        engine = self.engines.get(format)
        if not engine:
            raise ValueError(f"Unsupported format: {format}")

        assessment_items = engine().read_items(input_file)
        for item in assessment_items:
            self.item_bank.add_item(item)

    def write(self, output_file, format, verbose=False):
        engine = self.engines.get(format)
        if not engine:
            raise ValueError(f"Unsupported format: {format}")

        engine().write_items(output_file, self.item_bank.items)

    def summarize_items(self):
        self.item_bank.summarize_items()
```

---

### **2) Assessment Item Storage: `ItemBank`**
Since each **engine** (QTI 1.2, QTI 2.1, human-readable) handles file formats differently, all assessment items are converted into a **unified format** before being written back. The `ItemBank` class ensures that assessment items are stored **independently from any file format**.

```python
class ItemBank:
    def __init__(self):
        self.items = []

    def add_item(self, item: AssessmentItem):
        self.items.append(item)

    def summarize_items(self):
        summary = {}
        for item in self.items:
            summary[item.__class__.__name__] = summary.get(item.__class__.__name__, 0) + 1
        for item_type, count in summary.items():
            print(f"{item_type}: {count} items")
```

---

### **3) Internal Representation: `AssessmentItem` Classes**
Instead of storing assessment items as raw text or format-specific data, they are converted into structured **Python objects**.

```python
class AssessmentItem:
    def __init__(self, text, metadata=None):
        self.text = text
        self.metadata = metadata or {}

class MultipleChoice(AssessmentItem):
    def __init__(self, text, choices, answer):
        super().__init__(text)
        self.choices = choices
        self.answer = answer

class Matching(AssessmentItem):
    def __init__(self, text, pairs):
        super().__init__(text)
        self.pairs = pairs  # List of (prompt, correct match) pairs
```

---

## **Contributing**

### **Adding a New Engine**
To support a new format (e.g., JSON, CSV), create a folder in `engines/` and implement:

```python
class JSONEngine(BaseEngine):
    def read_items(self, json_file):
        # Convert JSON to AssessmentItem objects
        return items

    def write_items(self, json_file, items):
        # Convert AssessmentItem objects to JSON
        pass
```

### **Testing**
```bash
pytest tests/
```

### **Opening a Pull Request**
Once tested, submit a PR on GitHub!

---

## **License**
This project is licensed under the **LGPL v3 License**.

---
