odoo.define('hotel_booked_views.main', function (require) {
	"use strict";

	var config = require('web.config');
	var core = require('web.core');
	var dataComparisonUtils = require('web.dataComparisonUtils');
	var Domain = require('web.Domain');
	var fieldUtils = require('web.field_utils');
	var FormRenderer = require('web.FormRenderer');
	var FormView = require('web.FormView');
	var pyUtils = require('web.py_utils');
	var viewRegistry = require('web.view_registry');
	var rpc = require('web.rpc');
	var core = require('web.core');
	var _t = core._t;

	FormRenderer.include({

		events: _.extend({}, FormRenderer.prototype.events, {
			'click .actioncall': '_onactionCall',
		}),

		init: function (parent, state, params) {
			this._super.apply(this, arguments);
		},

		_updateView: function ($newContent) {
			this._super.apply(this, arguments);
		},
		_onactionCall: function (event) {
			var room_id = parseInt(event.target.id)
			var classstring = event.target.classList.value
			if (classstring.includes("available")) {
				this.do_action({
					name: _t('Hotel Room -  Available'),
					type: 'ir.actions.act_window',
					res_model: 'hotel.reservation',
					views: [[false, 'form']],
					view_mode: 'form',
					context: { 'default_room_id': room_id },
					target: 'new',
				});
			} else {
				this.do_action({
					name: _t('Reservation Booked'),
					type: 'ir.actions.act_window',
					res_model: 'hotel.reservation',
					res_id: room_id,
					views: [[false, 'form']],
					view_mode: 'form',
					target: 'new',
				});
			}
		},
	});

});
