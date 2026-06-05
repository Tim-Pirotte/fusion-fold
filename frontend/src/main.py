# pylint: disable=duplicate-code
"""Frontend app entrypoint."""

import flask as fl

app = fl.Flask(__name__)


def _render(page_name: str):
    return fl.render_template(page_name)

@app.route('/')
def index():
    return _render('index.html')

@app.route('/verify-account/<string:token>')
def verify_account(**_):
    return _render('verify_account.html')

if __name__ == '__main__':
    app.run(debug=False, threaded=True)
