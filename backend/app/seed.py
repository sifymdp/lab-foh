import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.core.security import hash_password
from app.models import DiningSession, Floor, MenuItem, Reservation, StatusHistory, Table, TableQRCode, User
from app.seed_data import DEMO_PASSWORD, DEMO_USERS, INITIAL_FLOOR, DEMO_MENU_ITEMS


def patch_camera_config(db: Session) -> None:
    """Backfill camera_url + roi_coords on existing DBs seeded before Phase 2."""
    from app.seed_data import DEMO_CAMERA_URL, _DEMO_ROIS

    changed = False
    for table in db.query(Table).all():
        if table.id not in _DEMO_ROIS:
            continue
        if not table.camera_url:
            table.camera_url = DEMO_CAMERA_URL
            changed = True
        if not table.roi_coords:
            table.roi_coords = json.dumps(_DEMO_ROIS[table.id])
            changed = True
    if changed:
        db.commit()


def patch_menu_items(db: Session) -> None:
    if db.query(MenuItem).count() > 0:
        return
    for item in DEMO_MENU_ITEMS:
        db.add(MenuItem(**item, id=new_id()))
    db.commit()


def seed_database(db: Session) -> None:
    if db.query(User).count() > 0:
        patch_camera_config(db)
        patch_menu_items(db)
        return

    now = datetime.now(timezone.utc)

    for u in DEMO_USERS:
        db.add(
            User(
                id=u["id"],
                name=u["name"],
                email=u["email"],
                role=u["role"],
                password_hash=hash_password(DEMO_PASSWORD),
                is_active=True,
                created_at=now,
            )
        )

    floor = Floor(
        id=INITIAL_FLOOR["id"],
        name=INITIAL_FLOOR["name"],
        width=INITIAL_FLOOR["width"],
        height=INITIAL_FLOOR["height"],
        sections=INITIAL_FLOOR["sections"],
        labels=INITIAL_FLOOR["labels"],
    )
    db.add(floor)

    for t in INITIAL_FLOOR["tables"]:
        cleaning_started = None
        if t.get("status") == "CLEANING":
            cleaning_started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        roi = t.get("roiCoords")
        table = Table(
            id=t["id"],
            floor_id=floor.id,
            section_id=t["sectionId"],
            number=t["number"],
            capacity=t["capacity"],
            type=t["type"],
            shape=t["shape"],
            status=t["status"],
            x=t["x"],
            y=t["y"],
            width=t["width"],
            height=t["height"],
            rotation=t["rotation"],
            camera_url=t.get("cameraUrl"),
            roi_coords=json.dumps(roi) if roi else None,
            cleaning_started_at=cleaning_started,
        )
        db.add(table)
        # generate a QR token for every table
        db.add(TableQRCode(id=new_id(), table_id=t["id"], token=new_id(), is_active=True))

    for item in DEMO_MENU_ITEMS:
        db.add(MenuItem(**item, id=new_id()))

    db.commit()


def empty_floor_layout(floor: Floor) -> None:
    w, h = floor.width, floor.height
    floor.sections = []
    floor.labels = [
        {
            "id": f"lbl-{new_id()}-ent",
            "kind": "ENTRANCE",
            "text": "Entrance",
            "bounds": {"x": w / 2 - 100, "y": h - 56, "width": 200, "height": 44},
        },
        {
            "id": f"lbl-{new_id()}-kit",
            "kind": "KITCHEN",
            "text": "Kitchen",
            "bounds": {"x": w - 140, "y": 12, "width": 120, "height": 44},
        },
    ]
