from app.models import Role, User


def test_create_admin_command(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["create-admin", "--email", "Admin@Example.com",
                                 "--password", "motdepasse123"])
    assert result.exit_code == 0, result.output
    assert User.query.filter_by(email="admin@example.com").one().role == Role.ADMIN

    again = runner.invoke(args=["create-admin", "--email", "admin@example.com",
                                "--password", "motdepasse123"])
    assert again.exit_code != 0
    assert "deja utilise" in again.output