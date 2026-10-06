import os

from flask import Flask, render_template, session

from admin import admin_bp
from auth import auth_bp
from citizen import citizen_bp
from config import Config
from services import ISSUE_TYPES, LOCATION_TYPES, start_sla_scheduler
from worker import worker_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    app.register_blueprint(auth_bp)
    app.register_blueprint(citizen_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(worker_bp)

    @app.route('/')
    def home():
        return render_template('index.html')

    @app.context_processor
    def global_template_data():
        return {
            'nav_issue_categories': list(ISSUE_TYPES.keys()),
            'nav_location_types': LOCATION_TYPES,
        }

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template('403.html'), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template('404.html'), 404

    @app.errorhandler(413)
    def too_large(_error):
        return render_template('413.html', max_mb=app.config['MAX_UPLOAD_MB']), 413

    @app.errorhandler(500)
    def server_error(_error):
        return render_template('500.html'), 500

    return app


app = create_app()

if __name__ == '__main__':
    debug = app.config['DEBUG']
    # With Flask's debug reloader, start the scheduler only in the serving process.
    if (not debug) or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        start_sla_scheduler(app)
    app.run(host='0.0.0.0', port=5000, debug=debug)
