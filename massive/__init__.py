# Massive Dynamic — Sistema de Gestión de Proyectos y Mantenimiento de Fixtures
# Cliente: Massive Dynamic / Ma. Fernanda Rocha
from flask import Blueprint

massive_bp = Blueprint("massive", __name__, url_prefix="/massive")

from . import views  # noqa: E402, F401
from . import analytics  # noqa: E402, F401
