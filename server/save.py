import json
import logging
import os
import secrets
import shutil
import sys

from peewee import (
    BooleanField,
    FloatField,
    ForeignKeyField,
    IntegerField,
    OperationalError,
    TextField,
)
from playhouse.migrate import fn, migrate, SqliteMigrator

from config import SAVE_FILE
from models import ALL_MODELS, Constants
from models.db import db

SAVE_VERSION = 26

logger: logging.Logger = logging.getLogger("PlanarAllyServer")
logger.setLevel(logging.INFO)


def upgrade(version):
    if version < 13:
        raise Exception(
            f"Upgrade code for this version is >1 year old and is no longer in the active codebase to reduce clutter. You can still find this code on github, contact me for more info."
        )
    elif version == 13:
        from models import LocationUserOption, MultiLine, Polygon

        db.foreign_keys = False
        migrator = SqliteMigrator(db)

        migrate(migrator.drop_column("location_user_option", "active_filters"))

        db.foreign_keys = True
        Constants.get().update(save_version=Constants.save_version + 1).execute()
    elif version == 14:
        db.foreign_keys = False
        migrator = SqliteMigrator(db)

        from models import GridLayer, Layer

        db.execute_sql(
            'CREATE TABLE IF NOT EXISTS "base_rect" ("shape_id" TEXT NOT NULL PRIMARY KEY, "width" REAL NOT NULL, "height" REAL NOT NULL, FOREIGN KEY ("shape_id") REFERENCES "shape" ("uuid") ON DELETE CASCADE)'
        )
        db.execute_sql(
            'CREATE TABLE IF NOT EXISTS "shape_type" ("shape_id" TEXT NOT NULL PRIMARY KEY, FOREIGN KEY ("shape_id") REFERENCES "shape" ("uuid") ON DELETE CASCADE)'
        )

        shape_types = [
            "asset_rect",
            "circle",
            "circular_token",
            "line",
            "multi_line",
            "polygon",
            "rect",
            "text",
        ]
        with db.atomic():
            for table in shape_types:
                db.execute_sql(
                    f"CREATE TEMPORARY TABLE _{table} AS SELECT * FROM {table}"
                )
                db.execute_sql(f"DROP TABLE {table}")
            for query in [
                'CREATE TABLE IF NOT EXISTS "asset_rect" ("shape_id" TEXT NOT NULL PRIMARY KEY, "width" REAL NOT NULL, "height" REAL NOT NULL, "src" TEXT NOT NULL, FOREIGN KEY ("shape_id") REFERENCES "shape" ("uuid") ON DELETE CASCADE)',
                'CREATE TABLE IF NOT EXISTS "circle" ("shape_id" TEXT NOT NULL PRIMARY KEY, "radius" REAL NOT NULL, FOREIGN KEY ("shape_id") REFERENCES "shape" ("uuid") ON DELETE CASCADE)',
                'CREATE TABLE IF NOT EXISTS "circular_token" ("shape_id" TEXT NOT NULL PRIMARY KEY, "radius" REAL NOT NULL, "text" TEXT NOT NULL, "font" TEXT NOT NULL, FOREIGN KEY ("shape_id") REFERENCES "shape" ("uuid") ON DELETE CASCADE)',
                'CREATE TABLE IF NOT EXISTS "line" ("shape_id" TEXT NOT NULL PRIMARY KEY, "x2" REAL NOT NULL, "y2" REAL NOT NULL, "line_width" INTEGER NOT NULL, FOREIGN KEY ("shape_id") REFERENCES "shape" ("uuid") ON DELETE CASCADE)',
                'CREATE TABLE IF NOT EXISTS "multi_line" ("shape_id" TEXT NOT NULL PRIMARY KEY, "line_width" INTEGER NOT NULL, "points" TEXT NOT NULL, FOREIGN KEY ("shape_id") REFERENCES "shape" ("uuid") ON DELETE CASCADE)',
                'CREATE TABLE IF NOT EXISTS "polygon" ("shape_id" TEXT NOT NULL PRIMARY KEY, "vertices" TEXT NOT NULL, FOREIGN KEY ("shape_id") REFERENCES "shape" ("uuid") ON DELETE CASCADE)',
                'CREATE TABLE IF NOT EXISTS "rect" ("shape_id" TEXT NOT NULL PRIMARY KEY, "width" REAL NOT NULL, "height" REAL NOT NULL, FOREIGN KEY ("shape_id") REFERENCES "shape" ("uuid") ON DELETE CASCADE)',
                'CREATE TABLE IF NOT EXISTS "text" ("shape_id" TEXT NOT NULL PRIMARY KEY, "text" TEXT NOT NULL, "font" TEXT NOT NULL, "angle" REAL NOT NULL, FOREIGN KEY ("shape_id") REFERENCES "shape" ("uuid") ON DELETE CASCADE)',
            ]:
                db.execute_sql(query)
            for table in shape_types:
                db.execute_sql(
                    f"INSERT INTO {table} SELECT _{table}.* FROM _{table} INNER JOIN shape ON shape.uuid = _{table}.uuid"
                )
        field = ForeignKeyField(Layer, Layer.id, null=True)
        with db.atomic():
            migrate(migrator.add_column("grid_layer", "layer_id", field))
            for gl in GridLayer.select():
                l = Layer.get_or_none(id=gl.id)
                if l:
                    gl.layer = l
                    gl.save()
                else:
                    gl.delete_instance()
            migrate(migrator.add_not_null("grid_layer", "layer_id"))

        db.foreign_keys = True
        Constants.get().update(save_version=Constants.save_version + 1).execute()
    elif version == 15:
        migrator = SqliteMigrator(db)
        db.foreign_keys = False
        with db.atomic():
            migrate(
                migrator.add_column("room", "is_locked", BooleanField(default=False))
            )
        db.foreign_keys = True
        Constants.get().update(save_version=Constants.save_version + 1).execute()
    elif version == 16:
        migrator = SqliteMigrator(db)
        db.foreign_keys = False
        with db.atomic():
            migrate(
                migrator.add_column(
                    "location", "unit_size_unit", TextField(default="ft")
                )
            )
        db.foreign_keys = True
        Constants.get().update(save_version=Constants.save_version + 1).execute()
    elif version == 17:
        migrator = SqliteMigrator(db)
        db.foreign_keys = False
        with db.atomic():
            migrate(
                migrator.add_column(
                    "polygon", "open_polygon", BooleanField(default=False)
                ),
                migrator.add_column("polygon", "line_width", IntegerField(default=2)),
            )
            db.execute_sql(
                "INSERT INTO polygon (shape_id, line_width, vertices, open_polygon) SELECT shape_id, line_width, points, 1 FROM multi_line"
            )
            db.execute_sql("DROP TABLE multi_line")
            db.execute_sql(
                "UPDATE shape SET type_ = 'polygon' WHERE type_ = 'multiline'"
            )
        db.foreign_keys = True
        Constants.get().update(save_version=Constants.save_version + 1).execute()
    elif version == 18:
        migrator = SqliteMigrator(db)
        db.foreign_keys = False
        with db.atomic():
            migrate(migrator.add_column("user", "email", TextField(null=True)))
        db.foreign_keys = True
        Constants.get().update(save_version=Constants.save_version + 1).execute()
    elif version == 19:
        db.foreign_keys = False
        migrator = SqliteMigrator(db)

        db.execute_sql(
            'CREATE TABLE IF NOT EXISTS "floor" ("id" INTEGER NOT NULL PRIMARY KEY, "location_id" INTEGER NOT NULL, "name" TEXT, "index" INTEGER NOT NULL, FOREIGN KEY ("location_id") REFERENCES "location" ("id") ON DELETE CASCADE)'
        )
        db.execute_sql(
            'INSERT INTO floor (location_id, name, "index") SELECT id, "ground", 0 FROM location'
        )

        with db.atomic():
            db.execute_sql("CREATE TEMPORARY TABLE _layer AS SELECT * FROM layer")
            db.execute_sql("DROP TABLE layer")
            db.execute_sql(
                'CREATE TABLE IF NOT EXISTS "layer" ("id" INTEGER NOT NULL PRIMARY KEY, "floor_id" INTEGER NOT NULL, "name" TEXT NOT NULL, "type_" TEXT NOT NULL, "player_visible" INTEGER NOT NULL, "player_editable" INTEGER NOT NULL, "selectable" INTEGER NOT NULL, "index" INTEGER NOT NULL, FOREIGN KEY ("floor_id") REFERENCES "floor" ("id") ON DELETE CASCADE)'
            )
            db.execute_sql(
                'INSERT INTO layer (id, floor_id, name, type_, player_visible, player_editable, selectable, "index") SELECT _layer.id, floor.id, _layer.name, type_, player_visible, player_editable, selectable, _layer."index" FROM _layer INNER JOIN floor ON floor.location_id = _layer.location_id'
            )

        db.foreign_keys = True
        Constants.get().update(save_version=Constants.save_version + 1).execute()
    elif version == 20:
        migrator = SqliteMigrator(db)
        db.foreign_keys = False
        with db.atomic():
            migrate(
                migrator.add_column("shape", "badge", IntegerField(default=1)),
                migrator.add_column("shape", "show_badge", BooleanField(default=False)),
            )
        db.foreign_keys = True
        Constants.get().update(save_version=Constants.save_version + 1).execute()
    elif version == 21:
        migrator = SqliteMigrator(db)
        db.foreign_keys = False
        with db.atomic():
            migrate(
                migrator.add_column("user", "invert_alt", BooleanField(default=False))
            )
        db.foreign_keys = True
        Constants.get().update(save_version=Constants.save_version + 1).execute()
    elif version == 22:
        migrator = SqliteMigrator(db)
        db.foreign_keys = False
        with db.atomic():
            db.execute_sql(
                'CREATE TABLE IF NOT EXISTS "marker" ("id" INTEGER NOT NULL PRIMARY KEY, "shape_id" TEXT NOT NULL, "user_id" INTEGER NOT NULL, "location_id" INTEGER NOT NULL, FOREIGN KEY ("shape_id") REFERENCES "shape"("uuid") ON DELETE CASCADE, FOREIGN KEY ("location_id") REFERENCES "location" ("id") ON DELETE CASCADE, FOREIGN KEY ("user_id") REFERENCES "user"("id") ON DELETE CASCADE)'
            )
        db.foreign_keys = True
        Constants.get().update(save_version=Constants.save_version + 1).execute()
    elif version == 23:
        migrator = SqliteMigrator(db)
        db.foreign_keys = False
        with db.atomic():
            migrate(
                migrator.add_column(
                    "shape_owner", "edit_access", BooleanField(default=True)
                ),
                migrator.add_column(
                    "shape_owner", "vision_access", BooleanField(default=True)
                ),
                migrator.add_column(
                    "shape", "default_edit_access", BooleanField(default=False)
                ),
                migrator.add_column(
                    "shape", "default_vision_access", BooleanField(default=False)
                ),
            )
        db.foreign_keys = True
        Constants.get().update(save_version=Constants.save_version + 1).execute()
    elif version == 24:
        migrator = SqliteMigrator(db)
        db.foreign_keys = False
        with db.atomic():
            db.execute_sql(
                'DELETE FROM "player_room" WHERE id IN (SELECT pr.id FROM "player_room" pr INNER JOIN "room" r ON r.id = pr.room_id WHERE r.creator_id = pr.player_id )'
            )
    elif version == 25:
        # Move Room.dm_location and Room.player_location to PlayerRoom.active_location
        # Add PlayerRoom.role
        # Add order index on location

        from models import Location

        migrator = SqliteMigrator(db)
        db.foreign_keys = False
        with db.atomic():
            migrate(
                migrator.add_column(
                    "player_room",
                    "active_location_id",
                    ForeignKeyField(
                        Location,
                        Location.id,
                        backref="players",
                        on_delete="CASCADE",
                        null=True,
                    ),
                ),
                migrator.add_column("player_room", "role", IntegerField(default=0)),
                migrator.add_column("location", "index", IntegerField(default=0)),
            )
            db.execute_sql(
                "UPDATE player_room SET active_location_id = (SELECT location.id FROM room INNER JOIN location ON room.id = location.room_id WHERE location.name = room.player_location AND room.id = player_room.room_id)"
            )
            db.execute_sql(
                "INSERT INTO player_room (role, player_id, room_id, active_location_id) SELECT 1, u.id, r.id, l.id FROM room r INNER JOIN user u ON u.id = r.creator_id INNER JOIN location l ON l.name = r.dm_location AND l.room_id = r.id"
            )
            db.execute_sql(
                "UPDATE location SET 'index' = (SELECT COUNT(*) + 1 FROM location l INNER JOIN room r WHERE location.room_id = r.id AND l.room_id = r.id AND l.'index' != 0) "
            )
            migrate(
                migrator.drop_column("room", "player_location"),
                migrator.drop_column("room", "dm_location"),
                migrator.add_not_null("player_room", "active_location_id"),
            )

        db.foreign_keys = True
        Constants.get().update(save_version=Constants.save_version + 1).execute()
    else:
        raise Exception(f"No upgrade code for save format {version} was found.")


def check_save():
    if not os.path.isfile(SAVE_FILE):
        logger.warning("Provided save file does not exist.  Creating a new one.")
        db.create_tables(ALL_MODELS)
        Constants.create(
            save_version=SAVE_VERSION, secret_token=secrets.token_bytes(32)
        )
    else:
        constants = Constants.get_or_none()
        if constants is None:
            logger.error(
                "Database does not conform to expected format. Failed to start."
            )
            sys.exit(2)
        if constants.save_version != SAVE_VERSION:
            logger.warning(
                f"Save format {constants.save_version} does not match the required version {SAVE_VERSION}!"
            )
            logger.warning("Attempting upgrade")

        updated = False
        while constants.save_version != SAVE_VERSION:
            updated = True
            logger.warning(
                f"Backing up old save as {SAVE_FILE}.{constants.save_version}"
            )
            shutil.copyfile(SAVE_FILE, f"{SAVE_FILE}.{constants.save_version}")
            logger.warning(f"Starting upgrade to {constants.save_version + 1}")
            try:
                upgrade(constants.save_version)
            except Exception as e:
                logger.exception(e)
                logger.error("ERROR: Could not start server")
                sys.exit(2)
                break
            else:
                logger.warning(f"Upgrade to {constants.save_version + 1} done.")
                constants = Constants.get()
        else:
            if updated:
                logger.warning("Upgrade process completed successfully.")
