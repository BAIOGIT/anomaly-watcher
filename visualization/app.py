"""Main Flask application for sensor data visualization."""
from flask import Flask, render_template, redirect, url_for
from .routes.dashboard import dashboard_bp

def create_app():
    """Create and configure Flask application."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key-here'
    
    # Register blueprints
    app.register_blueprint(dashboard_bp)
    
    @app.route('/')
    def index():
        """Main page - redirect to dashboard."""
        return redirect(url_for('dashboard.dashboard'))
    
    return app

if __name__ == '__main__':
    app = create_app()
    print("Starting Flask visualization server...")
    print("Access the dashboard at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)