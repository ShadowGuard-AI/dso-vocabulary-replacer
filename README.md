![Banner](banner.png)

# dso-vocabulary-replacer
A command-line tool that replaces sensitive terms in text files based on a user-provided vocabulary. Useful for replacing medical terms, slang, or other sensitive words with safer alternatives or placeholders. - Focused on Tools for sanitizing and obfuscating sensitive data within text files and structured data formats

## Install
`git clone https://github.com/ShadowStrikeHQ/dso-vocabulary-replacer`

## Usage
`python3 main.py input.txt vocabulary.txt output.txt [--randomize]`

Notes on behaviour:
- If the resolved output path is the input file (same path, a ./ alias, or a symlink to it), the run refuses at exit 1. The input is read fully before the output is opened.
- Matching is on word boundaries and is case insensitive: a vocabulary entry for cat does not change catalog, and an occurrence in a different case is still replaced. The replacement is inserted exactly as written in the vocabulary file.
- Every argument, including the --randomize vocabulary rule, is validated before any output file is opened, so a failed validation leaves a pre-existing output file unchanged.
- Vocabulary lines are split on the first comma only, so a replacement may contain commas. A line that still does not parse is logged, and the run reports a skipped count.
- The run counts replacements. If nothing is replaced, it prints a plain no terms replaced line and exits 1, with no success line and no output file.

## Parameters
- `-h`: Show help message and exit
- `--randomize`: Randomize replacements with Faker library. Requires vocabulary file with sensitive terms only.
- `--log_level`: No description provided

## License
Copyright (c) ShadowStrikeHQ
