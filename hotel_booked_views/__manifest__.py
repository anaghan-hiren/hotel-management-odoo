# -*- coding: utf-8 -*-

{
    "name": "Hotel Booked Views",
    "version": "15.0.1",
    "author": "Anaghan Hiren/anaghan.hiren",
    "summary": "Hotel Booked Views",
    "description": """Hotel Booked Views""",
    "category": "Hotel",
    "website": "https://www.linkedin.com/in/anaghan-heri/",
    "license": "AGPL-3.0",
    "depends": [
        "hotel",
        "hotel_reservation",
    ],
    "assets": {
        "web.assets_backend": [
            "hotel_booked_views/static/src/css/custom.css",
            "hotel_booked_views/static/src/js/main.js",
        ]
    },
    "data": [
        "data/demo.xml",
        "security/ir.model.access.csv",
        "views/hotel_availability.xml",
        "views/booked.xml",
        "views/room_status.xml",
    ],
    "qweb": [],
    "installable": True,
    "application": True,
    "auto_install": False,
}
