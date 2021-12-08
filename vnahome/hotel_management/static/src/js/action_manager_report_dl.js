odoo.define('hotel_management.ActionManager', function (require) {
"use strict";

/**
 * The purpose of this file is to add the support of Odoo actions of type
 * 'ir_actions_z_download_report' to the ActionManager.
 */

var ActionManager = require('web.ActionManager');
var crash_manager = require('web.CrashManager');
var framework = require('web.framework');
var session = require('web.session');

ActionManager.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Executes actions of type 'ir_actions_z_download_report'.
     *
     * @private
     * @param {Object} action the description of the action to execute
     * @returns {Deferred} resolved when the report has been downloaded ;
     *   rejected if an error occurred during the report generation
     */
    _executeVnaDownloadReportAction: function (action) {
        var self = this;
        framework.blockUI();
        return new Promise(function (resolve, reject) {
            session.get_file({
                url: '/vna_download_report',
                data: action.data,
                success: resolve,
                error: (error) => {
                    self.call('crash_manager', 'rpc_error', error);
                    reject();
                },
                complete: framework.unblockUI,
            });
        });
    },
    /**
     * Overrides to handle the 'ir_actions_z_download_report' actions.
     *
     * @override
     * @private
     */
    _handleAction: function (action, options) {
        if (action.type === 'ir_actions_vna_download_report') {
            return this._executeVnaDownloadReportAction(action, options);
        }
        return this._super.apply(this, arguments);
    },
});

});
