# app.py

import os
from app import create_app
from flask import send_from_directory

# Create Flask application
app = create_app(os.getenv('FLASK_ENV', 'development'))

@app.route('/uploads/company_logos/<filename>')
def uploaded_company_logo(filename):
    abs_dir = os.path.join(os.getcwd(), 'uploads', 'company_logos')
    abs_path = os.path.join(abs_dir, filename)
    print(f"➡️ Trying to serve file: {abs_path}")
    if not os.path.exists(abs_path):
        print("🚫 File not found!")
    return send_from_directory(abs_dir, filename)
if __name__ == '__main__':
    # Run the application
    app.run(
        host=os.getenv('FLASK_HOST', '127.0.0.1'),
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    )