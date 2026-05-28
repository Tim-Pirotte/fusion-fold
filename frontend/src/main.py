import json
import typing
import logging

import flask as fl
import pydantic as p

import db
import folding as f
import settings as s

app = fl.Flask(__name__)
app.logger.setLevel(logging.INFO)

settings = s.get_settings()
database = db.get_db(settings)

@app.errorhandler(p.ValidationError)
def handle_pydantic_validation_error(e):
    return fl.jsonify(e.errors()), 400

@app.errorhandler(db.DataBaseError)
def handle_database_error(e):
    app.logger.error("Database operation failed", exc_info=True)
    
    return '', 503

@app.route('/')
def index():
    return fl.render_template('index.html')

class SessionRequest(p.BaseModel):
    sequence: str = p.Field(min_length=settings.min_seq_len, max_length=settings.max_seq_len, pattern='^[AUGC]*$')
    folds_to_generate: int = p.Field(ge=settings.min_folds, le=settings.max_folds)
    steps_per_fold: int = p.Field(ge=settings.min_steps, le=settings.max_steps)
    return_noise: bool

@app.route('/api/generate-folding-session/', methods=['POST'])
def generate_folding_session():
    req = SessionRequest.model_validate(fl.request.get_json())
    session_id = db.create_session(database, req.model_dump_json())

    return { 'sessionId': session_id }, 200

@app.route('/api/stream-folding/<session_id>')
def stream_folding(session_id: str):
    session_str = db.get_session(database, session_id)
    session = SessionRequest.model_validate_json(session_str)

    return fl.Response(fl.stream_with_context(folding_streamer(session)), mimetype='text/event-stream')

def folding_streamer(session: SessionRequest) -> typing.Iterator[str]:
    try:
        for fold in f.folding_iterator(
            session.sequence, 
            session.folds_to_generate, 
            session.steps_per_fold,
            session.return_noise,
        ):
            yield f'data: {json.dumps(fold)}\n\n'

        app.logger.info('finished folding')

        yield "event: end\ndata: null\n\n"
    except (GeneratorExit, ConnectionResetError):
        app.logger.info('ending folding early due to client disconnect')

if __name__ == '__main__':
    app.run(debug=False, threaded=True)
