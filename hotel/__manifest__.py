# Copyright (C) 2022-TODAY Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Hotel Management",
    "version": "15.0.1.0.0",
    "author": "Odoo Community Association (OCA), Serpent Consulting \
               Services Pvt. Ltd., OpenERP SA",
    "category": "Hotel Management",
    "website": "https://github.com/OCA/vertical-hotel",
    "depends": ["sale_stock", "account"],
    "license": "LGPL-3",
    "summary": "Hotel Management to Manage Folio and Hotel Configuration",
    "demo": ["demo/hotel_data.xml"],
    "data": [
        "security/hotel_security.xml",
        "security/ir.model.access.csv",
        "data/hotel_sequence.xml",
        "report/report_view.xml",
        "report/hotel_folio_report_template.xml",
        "report/hotel_guest_list_template.xml",
        "report/meals_forcast_report.xml",
        "report/hotel_folio_services_report_template.xml",
        "views/hotel_folio.xml",
        "views/hotel_room.xml",
        "views/hotel_room_amenities.xml",
        "views/hotel_room_type.xml",
        "views/hotel_service_type.xml",
        "views/hotel_services.xml",
        "views/product_product.xml",
        "views/res_company.xml",
        "views/actions.xml",
        "views/menus.xml",
        "wizard/hotel_wizard.xml",
        "wizard/guest_wizard.xml",
        "wizard/meals_forcast_view.xml"
    ],
    "assets": {
        "web.assets_backend": ["hotel/static/src/css/room_kanban.css"],
    },
    "external_dependencies": {"python": ["python-dateutil"]},
    "images": ["static/description/Hotel.png"],
    "application": True,
}
