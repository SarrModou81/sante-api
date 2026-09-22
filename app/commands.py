import click

from app.errors import APIError
from app.services import auth_service


def register_commands(app):
    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(email, password):
        """Cree un compte administrateur (seul moyen d'obtenir le role admin)."""
        try:
            user = auth_service.create_admin(email, password)
        except APIError as err:
            raise click.ClickException(err.message)
        click.echo(f"Administrateur cree : {user.email} (id={user.id})")