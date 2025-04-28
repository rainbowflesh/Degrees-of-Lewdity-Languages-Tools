# Degrees-of-Lewdity-Languages-Tools

# WIP

This project include 3 tools:

- Dumper: dump translatable raw strings from game
- Parser: parse raw strings to human readable
- Translator: machine translator provide online and local model

![banner](./assets/banner.png)

## Usage

```sh
poetry install --no-root
poetry run python run.py --help
```

### Create diff files

```sh
poetry run python run.py --diff dicts/translated/zh-Hans/dol dicts/raw/dolp dicts/diff/dolp
```

### Use machine translation

```sh
cp .env.template .env
seed YOUR_API_TOKEN >> .env
poetry run python run.py --help
```

#### Use MT with local models

```sh
conda env create -f conda-env.yaml
# for further usage
# remember activate conda first
# otherwise you will encounter this https://www.explainxkcd.com/wiki/images/c/cb/python_environment.png
conda activate dol-mt

poetry config virtualenvs.create false
poetry install --no-root

poetry run python run.py --help
```

### Test

```sh
poetry run pytest tests
```
