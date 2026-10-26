# Import Appendices tool

This is a small CLI tool for processing and importing the content of Word (`.docx`) documents for
question info appendices into the database.

The main requirement for these documents are, that headers for individual sections in the document
have to be of type "Heading 2", as the tool will split the document based on `<h2>` headings after
conversion into HTML.

#### How it works

Before importing, the document will be converted into HTML. There, the tool will extract any media
(i.e. images) into the static assets directory in the frontend (`/frontend/static`). After that, the
HTML will be sanitized and specific formatting will be applied. Then the HTML will be split into
sections, each of which getting stored separately in the database.

## Prerequisites

- [Python](https://www.python.org/) version 3.12 or higher
  > Check your version by running: `python3 --version`

## Installation

Follow these steps to setup your local development environment:

1. Create a Virtual Environment

```sh
# Change to tool directory
cd tools/import-appendices/

# Create the environment
python3 -m venv .venv

# Activate the environment (Unix/macOS)
source .venv/bin/activate

# Activate the environment (Windows)
.venv\Scripts\activate
```

2. Install Dependencies

```sh
pip install -r requirements.txt
```

3. Install the Tool

```sh
pip install -e .
```

The tool will be installed in _editable_ mode into the current virtual environment.

## Usage

Make sure the virtual environment is activated:

```sh
# /tools/import-appendices
source .venv/bin/activate
```

Then you can use:

```sh
import-appendices <document.docx> <question_id>
```

### CLI Reference

A description for the following arguments and options can also be viewed from the command-line:

```sh
import-appendices --help
```

#### Arguments

- `document.docx`: Path to the Word document to import
- `question_id`: ID of the question (`questionId` inside the database) this document belongs to

#### Options

- `--no-fix-paragraphs`: Don't fix split paragraphs (by default, the tool tries to join paragraph back
  together in case they got separated after conversion into HTML; this can potentially lead to issues
  in edge-case scenarios that haven't been considered yet)

### Example

```sh
import-appendices ~/Documents/Anhang\ I-I-2a\ Sichere\ Marktbereitstellung.docx 11
```

### Mappings

As it's tedious having to look up the question ID from the database every time a new document
version is ready for importing, I created a `mappings.json` file that matches IDs with document
names for currently already imported documents.

If at some point the questions in the database are changed (e.g. removed, then readded), this file will
have to be updated, or at least not taken as reference anymore.
