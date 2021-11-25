set -e
mypy coin --strict
black coin
echo "Passed!"
