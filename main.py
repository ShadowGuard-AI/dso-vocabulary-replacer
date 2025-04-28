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
    """
    Loads the vocabulary from the specified file.

    Args:
        vocabulary_file (str): The path to the vocabulary file.

    Returns:
        dict: A dictionary containing the vocabulary (sensitive term as key, replacement term as value).
              Returns None if there's an error loading the file.
    """
    vocabulary = {}
    try:
        with open(vocabulary_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    parts = line.split(',')
                    if len(parts) == 2:
                        sensitive_term = parts[0].strip()
                        replacement_term = parts[1].strip()
                        vocabulary[sensitive_term] = replacement_term
                    elif len(parts) == 1:
                        sensitive_term = parts[0].strip()
                        vocabulary[sensitive_term] = None #Mark that this should be randomized
                    else:
                        logging.warning(f"Invalid line in vocabulary file: {line}. Skipping.")
    except FileNotFoundError:
        logging.error(f"Vocabulary file not found: {vocabulary_file}")
        return None
    except Exception as e:
        logging.error(f"Error loading vocabulary file: {e}")
        return None
    return vocabulary

def replace_terms(input_file, vocabulary, output_file, randomize):
    """
    Replaces sensitive terms in the input file with replacement terms from the vocabulary.

    Args:
        input_file (str): The path to the input file.
        vocabulary (dict): A dictionary containing the vocabulary.
        output_file (str): The path to the output file.
        randomize (bool): If True, generate random replacements.
    """
    try:
        # Detect encoding
        with open(input_file, 'rb') as f:
            rawdata = f.read()
            result = chardet.detect(rawdata)
            encoding = result['encoding']

        with open(input_file, 'r', encoding=encoding) as infile, open(output_file, 'w', encoding='utf-8') as outfile:
            text = infile.read()
            if randomize:
                fake = Faker()
                for sensitive_term in vocabulary:
                    if vocabulary[sensitive_term] is None: #Randomize
                      text = text.replace(sensitive_term, fake.name())
                    else:
                      logging.error("Vocabulary must only contain sensitive terms when using --randomize")
                      return 1 # Exit status

            else:
                for sensitive_term, replacement_term in vocabulary.items():
                    text = text.replace(sensitive_term, replacement_term)

            outfile.write(text)
        logging.info(f"Successfully replaced terms in {input_file} and saved to {output_file}")
        return 0 #Success
    except FileNotFoundError:
        logging.error(f"Input file not found: {input_file}")
        return 1
    except Exception as e:
        logging.error(f"Error processing file: {e}")
        return 1

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

    vocabulary = load_vocabulary(args.vocabulary_file)
    if vocabulary is None:
        sys.exit(1)

    exit_code = replace_terms(args.input_file, vocabulary, args.output_file, args.randomize)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()