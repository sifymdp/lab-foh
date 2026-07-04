"""Initial data matching frontend/src/mock/data.ts"""

DEMO_PASSWORD = "demo1234"

DEMO_USERS = [
    {"id": "u-owner", "name": "Alex Owner", "email": "owner@foh.demo", "role": "OWNER"},
    {"id": "u-manager", "name": "Morgan Manager", "email": "manager@foh.demo", "role": "MANAGER"},
    {"id": "u-host", "name": "Hannah Host", "email": "host@foh.demo", "role": "HOST"},
    {"id": "u-waiter", "name": "Wade Waiter", "email": "waiter@foh.demo", "role": "WAITER"},
]

INITIAL_FLOOR = {
    "id": "floor-1",
    "name": "Main Dining",
    "width": 1000,
    "height": 620,
    "sections": [
        {
            "id": "sec-indoor",
            "name": "Indoor",
            "color": "#818cf8",
            "bounds": {"x": 40, "y": 48, "width": 580, "height": 300},
        },
        {
            "id": "sec-outdoor",
            "name": "Outdoor",
            "color": "#38bdf8",
            "bounds": {"x": 40, "y": 380, "width": 420, "height": 200},
        },
        {
            "id": "sec-bar",
            "name": "Bar",
            "color": "#fbbf24",
            "bounds": {"x": 680, "y": 48, "width": 280, "height": 300},
        },
    ],
    "labels": [
        {
            "id": "lbl-entrance",
            "kind": "ENTRANCE",
            "text": "Entrance",
            "bounds": {"x": 400, "y": 564, "width": 200, "height": 44},
        },
        {
            "id": "lbl-kitchen",
            "kind": "KITCHEN",
            "text": "Kitchen",
            "bounds": {"x": 860, "y": 12, "width": 120, "height": 44},
        },
    ],
}

DEMO_CAMERA_URL = r"C:/Users/lucky/demo_video.mp4"

# Demo ROI regions on the shared camera frame (640×480 reference layout)
_DEMO_ROIS = {
    "t-1":  {"x": 40,  "y": 60,  "width": 120, "height": 100},
    "t-2":  {"x": 180, "y": 55,  "width": 130, "height": 110},
    "t-3":  {"x": 330, "y": 50,  "width": 140, "height": 115},
    "t-4":  {"x": 490, "y": 45,  "width": 140, "height": 120},
    "t-5":  {"x": 40,  "y": 190, "width": 130, "height": 110},
    "t-6":  {"x": 40,  "y": 330, "width": 140, "height": 110},
    "t-7":  {"x": 200, "y": 340, "width": 100, "height": 100},
    "t-8":  {"x": 400, "y": 80,  "width": 90,  "height": 90},
    "t-9":  {"x": 510, "y": 80,  "width": 90,  "height": 90},
    "t-10": {"x": 455, "y": 190, "width": 90,  "height": 90},
}

INITIAL_FLOOR["tables"] = [
        {"id": "t-1", "sectionId": "sec-indoor", "number": "1", "capacity": 2, "type": "STANDARD", "shape": "CIRCLE", "status": "AVAILABLE", "x": 120, "y": 120, "width": 64, "height": 64, "rotation": 0, "cameraUrl": DEMO_CAMERA_URL, "roiCoords": _DEMO_ROIS["t-1"]},
        {"id": "t-2", "sectionId": "sec-indoor", "number": "2", "capacity": 4, "type": "STANDARD", "shape": "RECTANGLE", "status": "AVAILABLE", "x": 220, "y": 110, "width": 90, "height": 70, "rotation": 0, "cameraUrl": DEMO_CAMERA_URL, "roiCoords": _DEMO_ROIS["t-2"]},
        {"id": "t-3", "sectionId": "sec-indoor", "number": "3", "capacity": 6, "type": "BOOTH", "shape": "RECTANGLE", "status": "RESERVED", "x": 360, "y": 100, "width": 110, "height": 85, "rotation": 0, "cameraUrl": DEMO_CAMERA_URL, "roiCoords": _DEMO_ROIS["t-3"]},
        {"id": "t-4", "sectionId": "sec-indoor", "number": "4", "capacity": 8, "type": "VIP", "shape": "RECTANGLE", "status": "AVAILABLE", "x": 520, "y": 95, "width": 120, "height": 95, "rotation": 0, "cameraUrl": DEMO_CAMERA_URL, "roiCoords": _DEMO_ROIS["t-4"]},
        {"id": "t-5", "sectionId": "sec-indoor", "number": "5", "capacity": 4, "type": "STANDARD", "shape": "RECTANGLE", "status": "AVAILABLE", "x": 120, "y": 230, "width": 88, "height": 72, "rotation": 0, "cameraUrl": DEMO_CAMERA_URL, "roiCoords": _DEMO_ROIS["t-5"]},
        {"id": "t-6", "sectionId": "sec-outdoor", "number": "P1", "capacity": 4, "type": "STANDARD", "shape": "RECTANGLE", "status": "AVAILABLE", "x": 120, "y": 400, "width": 92, "height": 72, "rotation": 0, "cameraUrl": DEMO_CAMERA_URL, "roiCoords": _DEMO_ROIS["t-6"]},
        {"id": "t-7", "sectionId": "sec-outdoor", "number": "P2", "capacity": 2, "type": "STANDARD", "shape": "CIRCLE", "status": "AVAILABLE", "x": 250, "y": 410, "width": 64, "height": 64, "rotation": 0, "cameraUrl": DEMO_CAMERA_URL, "roiCoords": _DEMO_ROIS["t-7"]},
        {"id": "t-8", "sectionId": "sec-bar", "number": "B1", "capacity": 2, "type": "BAR", "shape": "CIRCLE", "status": "AVAILABLE", "x": 780, "y": 140, "width": 56, "height": 56, "rotation": 0, "cameraUrl": DEMO_CAMERA_URL, "roiCoords": _DEMO_ROIS["t-8"]},
        {"id": "t-9", "sectionId": "sec-bar", "number": "B2", "capacity": 2, "type": "BAR", "shape": "CIRCLE", "status": "CLEANING", "x": 860, "y": 140, "width": 56, "height": 56, "rotation": 0, "cameraUrl": DEMO_CAMERA_URL, "roiCoords": _DEMO_ROIS["t-9"]},
        {"id": "t-10", "sectionId": "sec-bar", "number": "B3", "capacity": 2, "type": "BAR", "shape": "CIRCLE", "status": "AVAILABLE", "x": 820, "y": 220, "width": 56, "height": 56, "rotation": 0, "cameraUrl": DEMO_CAMERA_URL, "roiCoords": _DEMO_ROIS["t-10"]},
]

DEMO_MENU_ITEMS = [
    {"name": "Garlic Bread",        "description": "Toasted sourdough with garlic butter", "price": 4.50,  "category": "Starters",  "available": True,  "display_order": 1},
    {"name": "Soup of the Day",     "description": "Ask your server for today's selection",  "price": 5.00,  "category": "Starters",  "available": True,  "display_order": 2},
    {"name": "Grilled Salmon",      "description": "With seasonal vegetables and lemon butter","price": 18.50, "category": "Mains",     "available": True,  "display_order": 1},
    {"name": "Margherita Pizza",    "description": "San Marzano tomato, buffalo mozzarella", "price": 13.00, "category": "Mains",     "available": True,  "display_order": 2},
    {"name": "Ribeye Steak",        "description": "250g, served with fries and side salad", "price": 26.00, "category": "Mains",     "available": True,  "display_order": 3},
    {"name": "Chocolate Fondant",   "description": "Warm, with vanilla ice cream",           "price": 7.00,  "category": "Desserts",  "available": True,  "display_order": 1},
    {"name": "Tiramisu",            "description": "Classic mascarpone and espresso",        "price": 6.50,  "category": "Desserts",  "available": True,  "display_order": 2},
    {"name": "Sparkling Water",     "description": "500ml bottle",                            "price": 2.50,  "category": "Drinks",    "available": True,  "display_order": 1},
    {"name": "House Red Wine",      "description": "175ml glass",                             "price": 6.50,  "category": "Drinks",    "available": True,  "display_order": 2},
    {"name": "Soft Drink",          "description": "Coke, Diet Coke, Lemonade, OJ",          "price": 3.00,  "category": "Drinks",    "available": True,  "display_order": 3},
]
