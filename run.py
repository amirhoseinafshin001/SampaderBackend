# import tests.db
# import tests.services
# import tests.JWToken
# import tests.image_service
# import tests.post_creator

from api import create_app
from admin import admin_bp

app = create_app()
app.register_blueprint(admin_bp)

if __name__ == "__main__":
    print("starting the app.")
    app.run(debug=True)
