## Building docs locally

Before building the docs locally, you will need to follow the [development quickstart](./development_quickstart.md) to set up the necessary environment. You cannot skip this step, because some Splink docs Markdown is auto-generated using the Splink development environment.

Once you've done that,
to rapidly build the documentation and immediately see changes you've made you can use [this script](https://github.com/moj-analytical-services/splink/blob/master/scripts/make_docs_locally.sh)
**outside your Poetry virtual environment**:

```sh
source scripts/make_docs_locally.sh
```

This is much faster than waiting for GitHub actions to run if you're trying to make fiddly changes to formatting etc.

Once you've finished updating Splink documentation we ask that you run our spellchecker. Instructions on how to do this are given below.

## Spellchecking docs

When updating Splink documentation, we ask that you run our spellchecker before submitting a pull request. This is to help ensure quality and consistency across the documentation. Please note, the spellchecker _only works on markdown files_.

To run the spellchecker on either a single markdown file or folder of markdown files, you can use the following script:

```sh
source scripts/pyspelling/spellchecker.sh <path_to_file_or_folder>
```

Omitting the file/folder path will run the spellchecker on all markdown files contained in the `docs` folder. We recommend running the spellchecker only on files that you have created or edited. 

The spellchecker uses the Python package [PySpelling](https://facelessuser.github.io/pyspelling/) and its underlying spellchecking tool, Aspell. Running the above script will automatically install these packages along with any other necessary dependencies.

The spellchecker compares words to a [standard dictionary](https://github.com/LibreOffice/dictionaries/blob/master/en/en_GB.aff) and a custom dictionary (`scripts/pyspelling/custom_dictionary.txt`) of words. If no spelling mistakes are found, you will see the following terminal printout:

```sh

Spelling check passed :)

```

otherwise, PySpelling will printout the spelling mistakes found in each file.

Correct spellings of words not found in a standard dictionary (e.g. Splink) can be recorded as such by adding them to `scripts/pyspelling/custom_dictionary.txt`. (Don't worry about adding them in alphabetical order or accidental duplication as this will be handled automatically by a GitHub Action.)

Please correct any mistakes found or update the custom dictionary to ensure the spellchecker passes before putting in a pull request containing updates to the documentation.

!!! note

    The spellchecker is configured (via `pyspelling.yml`) to ignore text between certain delimiters to minimise picking up Splink/programming-specific terms. If there are additional patterns that you think should be excepted then please let us know in your pull request.

    The custom dictionary deliberately contains a small number of misspelled words (e.g. “Siohban”). These are sometimes necessary where we are explaining how Splink handles typos in data records.



   

 



