"""Import every domain's SQLAlchemy models so Base.metadata has the full FK graph.

Any process that flushes/saves ORM objects (api, bot, worker, alembic, tests) must
import this first — SQLAlchemy needs every referenced table registered on the shared
metadata to resolve cross-module foreign keys, even for tables it isn't touching
directly (e.g. saving a Document needs `patients` registered too).
"""

from app.auth import models as auth_models  # noqa: F401
from app.patient import models as patient_models  # noqa: F401
from app.documents import models as documents_models  # noqa: F401
from app.extraction import models as extraction_models  # noqa: F401
from app.visits import models as visits_models  # noqa: F401
from app.treatment import models as treatment_models  # noqa: F401
from app.assistant import models as assistant_models  # noqa: F401
