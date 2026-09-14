def register_blueprints(app):
    from .auth import bp as auth_bp
    from .dashboard import bp as dashboard_bp
    from .countries import bp as countries_bp
    from .cities import bp as cities_bp
    from .wishlist import bp as wishlist_bp
    from .visited import bp as visited_bp
    from .trips import bp as trips_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(countries_bp)
    app.register_blueprint(cities_bp)
    app.register_blueprint(wishlist_bp)
    app.register_blueprint(visited_bp)
    app.register_blueprint(trips_bp)
