import argparse
import logging
import os
import sys
import chardet
from faker import Faker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_argparse():
    """
    Sets up the argument parser for the command-line interface.
    """
    parser = argparse.ArgumentParser(
        description="Replaces sensitive terms in text files based on a user-provided vocabulary."
    )
    parser.add_argument(
        "input_file",
        help="The path to the input text file."
    )
    parser.add_argument(
        "vocabulary_file",
        help="The path to the vocabulary file (CSV or TXT). Each line should contain 'sensitive_term,replacement_term'."
    )
    parser.add_argument(
        "output_file",
        help="The path to the output text file."
    )
    parser.add_argument(
        "--randomize",
        action="store_true",
        help="Randomize replacements with Faker library. Requires vocabulary file with sensitive terms only."
    )
    parser.add_argument(
        "--log_level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help="Set the logging level (default: INFO)"
    )
    return parser

def load_vocabulary(vocabulary_file):
    """Load vocabulary. Returns (vocabulary, skipped_count) or (None, 0) on load error.
    Lines are split on the first comma only, so a replacement may contain commas.
    A line with no comma is a term only entry (for --randomize). A line whose term
    is empty does not parse: it is logged and counted as skipped."""
    vocabulary = {}
    skipped = 0
    try:
        with open(vocabulary_file, 'r', encoding='utf-8') as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue
                if ',' in raw:
                    sensitive_term, replacement_term = raw.split(',', 1)
                    sensitive_term = sensitive_term.strip(); replacement_term = replacement_term.strip()
                    if not sensitive_term:
                        skipped += 1; logging.warning(f"Invalid line in vocabulary file: {raw}. Skipping."); continue
                    # Later lines win. A term listed twice keeps only its last replacement,
                    # and the dict preserves first insertion order, which also fixes the
                    # order the replacement passes run in replace_terms.
                    vocabulary[sensitive_term] = replacement_term
                else:
                    sensitive_term = raw.strip()
                    if not sensitive_term:
                        skipped += 1; logging.warning(f"Invalid line in vocabulary file: {raw}. Skipping."); continue
                    vocabulary[sensitive_term] = None
    except FileNotFoundError:
        logging.error(f"Vocabulary file not found: {vocabulary_file}")
        return None, 0
    except Exception as e:
        logging.error(f"Error loading vocabulary file: {e}")
        return None, 0
    if skipped:
        logging.warning(f"Skipped {skipped} vocabulary line(s) that did not parse.")
    return vocabulary, skipped

def replace_terms(input_file, vocabulary, output_file, randomize):
    """Replace terms. Input is read fully before the output is opened.
    All validation runs before the output is opened. Returns (exit_code, count)."""
    import re
    # Validate every argument before any output file is opened.
    if randomize:
        for term, repl in vocabulary.items():
            if repl is not None:
                logging.error("Vocabulary must only contain sensitive terms when using --randomize")
                return 1, 0
    if not vocabulary:
        print("No terms replaced.")
        return 1, 0
    try:
        with open(input_file, 'rb') as f:
            rawdata = f.read()
            result = chardet.detect(rawdata)
            encoding = result['encoding'] or 'utf-8'
        text = rawdata.decode(encoding)
    except FileNotFoundError:
        logging.error(f"Input file not found: {input_file}")
        return 1, 0
    except Exception as e:
        logging.error(f"Error processing file: {e}")
        return 1, 0
    # Both branches below build the same pattern shape: the escaped term
    # between two word boundaries, matched without case. The boundaries keep
    # a term from matching inside a longer word, but a term that starts or
    # ends with punctuation can fail to match at a real word edge, because a
    # boundary needs a word character on one side. Matching ignores case and
    # the replacement goes in as written, so the original case is lost.
    # Passes run in vocabulary order over each other's output, so a
    # replacement that contains a later sensitive term gets replaced again.
    total = 0
    if randomize:
        fake = Faker()
        for sensitive_term in vocabulary:
            replacement = fake.name()
            pattern = re.compile(r'\b' + re.escape(sensitive_term) + r'\b', re.IGNORECASE)
            # The replacement goes through a lambda, not a replacement string, so
            # backslashes and group references in the fake name are inserted
            # literally instead of being read as escapes. One fake name is drawn per
            # term, so every occurrence of that term gets the same name and the text
            # stays consistent with itself.
            text, n = pattern.subn(lambda m, r=replacement: r, text)
            total += n
    else:
        for sensitive_term, replacement_term in vocabulary.items():
            # Term only entries are skipped silently outside randomize mode. The same
            # mixed vocabulary is a hard error with --randomize, checked at the top
            # of this function before the input is even read.
            if replacement_term is None:
                continue
            pattern = re.compile(r'\b' + re.escape(sensitive_term) + r'\b', re.IGNORECASE)
            text, n = pattern.subn(lambda m, r=replacement_term: r, text)
            total += n
    logging.info(f"Replacements: {total}")
    if total == 0:
        print("No terms replaced.")
        return 1, 0
    try:
        # Output is always utf-8, whatever encoding was detected for the input.
        # The text was decoded to str on the way in, so this is a conversion,
        # not a corruption, but a caller diffing bytes should know it happened.
        with open(output_file, 'w', encoding='utf-8') as outfile:
            outfile.write(text)
    except Exception as e:
        logging.error(f"Error processing file: {e}")
        return 1, 0
    logging.info(f"Successfully replaced terms in {input_file} and saved to {output_file}")
    return 0, total

def main():
    """
    Main function to execute the vocabulary replacement.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    # Set logging level
    logging.getLogger().setLevel(args.log_level.upper())

    # Input validation
    if not os.path.exists(args.input_file):
        logging.error(f"Input file does not exist: {args.input_file}")
        sys.exit(1)
    if not os.path.exists(args.vocabulary_file):
        logging.error(f"Vocabulary file does not exist: {args.vocabulary_file}")
        sys.exit(1)

    # Same-path guard before anything is opened for write.
    from pathlib import Path as _P
    try:
        if _P(args.input_file).resolve() == _P(args.output_file).resolve():
            logging.error("Output path resolves to the input file. Refusing to overwrite the input.")
            sys.exit(1)
    except SystemExit:
        raise
    except Exception:
        pass
    vocabulary, skipped_count = load_vocabulary(args.vocabulary_file)
    if vocabulary is None:
        sys.exit(1)
    if skipped_count:
        logging.warning(f"Vocabulary lines skipped: {skipped_count}")
    exit_code, _count = replace_terms(args.input_file, vocabulary, args.output_file, args.randomize)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()