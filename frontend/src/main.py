import flask as fl

app = fl.Flask(__name__)

@app.route('/')
def index():
    return fl.render_template('index.html')

@app.route('/login')
def login():
    return fl.render_template('login.html')

@app.route('/verify-account/<string:token>')
def verify_account(**_):
    return fl.render_template('verify_account.html')

@app.route('/reset-password')
def reset_password():
    return fl.render_template('reset_password.html')

@app.route('/reset-password/<string:token>')
def complete_password_reset(**_):
    return fl.render_template('complete_password_reset.html')

if __name__ == '__main__':
    app.run(debug=False, threaded=True)
