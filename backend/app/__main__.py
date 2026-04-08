# This lets the project run with python -m app.
from . import app


if __name__ == "__main__":
    app.run(debug=False)
