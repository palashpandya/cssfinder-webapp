from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from logic import find_css, find_css_stream
import os
import json
import queue
import threading

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/theory')
def theory():
    return render_template('theory.html')

@app.route('/run', methods=['POST'])
def run():
    data = request.json
    state = data.get('state')
    number = data.get('number')
    trials = data.get('trials')
    try:
        rhocss, mindist, plot = find_css(state, number, trials)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({
        "matrix": rhocss,
        "number": mindist,
        "plot": plot
    })

@app.route('/run-stream')
def run_stream():
    state = request.args.get('state')
    number = request.args.get('number')
    trials = request.args.get('trials')

    q = queue.Queue()

    def worker():
        try:
            def on_progress(itr, max_iter, trial_count, max_trials, dist):
                q.put(('progress', {'itr': itr, 'max_iter': max_iter,
                                    'trials': trial_count, 'max_trials': max_trials,
                                    'dist': dist}))
            matrix, mindist, plot = find_css_stream(state, number, trials, on_progress)
            q.put(('done', (matrix, mindist, plot)))
        except Exception as e:
            q.put(('error', str(e)))

    threading.Thread(target=worker, daemon=True).start()

    def generate():
        while True:
            msg_type, payload = q.get()
            if msg_type == 'progress':
                yield f"data: {json.dumps({'type': 'progress', **payload})}\n\n"
            elif msg_type == 'done':
                matrix, mindist, plot = payload
                yield f"data: {json.dumps({'type': 'done', 'matrix': matrix, 'number': mindist, 'plot': plot})}\n\n"
                break
            elif msg_type == 'error':
                yield f"data: {json.dumps({'type': 'error', 'message': payload})}\n\n"
                break

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host='0.0.0.0', port=port)
