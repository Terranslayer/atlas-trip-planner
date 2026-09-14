import click

from .repos.sqlite import close_conn, init_schema


def init_db(app):
    app.teardown_appcontext(close_conn)

    @app.cli.command("init-db")
    def cli_init_db():
        init_schema()
        click.echo(f"schema initialized at {app.config['SQLITE_PATH']}")

    @app.cli.command("refresh-advisories")
    def cli_refresh_advisories():
        from .services import advisory
        n = advisory.refresh()
        click.echo(f"advisories upserted: {n}")
