if [[ "$VIRTUAL_ENV" == "" ]]; then
  source "./venv-linux/bin/activate"
fi

pylint ./tests | { grep "unused-import" || true; }
pylint ./PyPDFForm | { grep "unused-import" || true; }
