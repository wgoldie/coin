set -e
mypy --config mypy.ini coin --strict
black coin
echo "Passed!"
