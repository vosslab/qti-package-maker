# Usage

qti_package_maker converts Blackboard Question Upload (BBQ) text files into QTI
packages and other exports using [tools/bbq_converter.py](../tools/bbq_converter.py).

## Quick start
```sh
python3 tools/bbq_converter.py -i bbq-example-questions.txt -1
```

```sh
python3 tools/bbq_converter.py -i bbq-example-questions.txt --all
```

Input files must follow the `bbq-<name>-questions.txt` naming pattern. See
[docs/FORMATS.md](FORMATS.md) for the BBQ format details.

## CLI
```sh
python3 tools/bbq_converter.py -h
```

Common flags:
- `-i`, `--input`: Path to the BBQ text file.
- `-f`, `--format`: One or more output engines.
- `-a`, `--all`: Enable all output formats.
- `-1`, `--qti12`: Canvas QTI v1.2 output.
- `-2`, `--qti21`: Blackboard QTI v2.1 output.
- `-u`, `--ultra`: Blackboard Ultra QTI v2.1 output.
- `-B`, `--bbexport`: Blackboard pool export ZIP output.
- `--allow-mixed`: Allow mixed question types in one run.

## Examples
```sh
python3 tools/bbq_converter.py -i bbq-example-questions.txt -f canvas_qti_v1_2 -f human_readable
```

```sh
python3 tools/bbq_converter.py -i bbq-example-questions.txt -r
```

## Inputs and outputs
- Inputs: tab-delimited BBQ text files; see [docs/FORMATS.md](FORMATS.md).
- Outputs: format-specific artifacts produced by the selected engines; see
  [docs/ENGINES.md](ENGINES.md).

## Known gaps
- Document output file naming conventions per engine.
- Confirm whether any non-BBQ input formats are supported beyond BBQ text.
