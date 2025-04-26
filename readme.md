# Dumper

## Usage

```sh
poetry install --no-root
poetry run python run.py --help
```

### Use MT

```sh
cp .env.template .env
seed YOUR_API_TOKEN >> .env
poetry run python run.py --help
```

### Use MT with local models

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
