set -e
flake8 --ignore=E501,W503
mypy --config mypy.ini coin --strict
black coin
echo "Passed!"
