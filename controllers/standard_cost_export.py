from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import content_disposition, request


class IndoorStandardCostExportController(http.Controller):

    @http.route(
        "/indoor_inventario/standard_cost_batch/<int:batch_id>/xlsx",
        type="http",
        auth="user",
    )
    def export_standard_cost_batch(self, batch_id, **kwargs):
        batch = request.env["indoor.standard.cost.batch"].browse(batch_id).exists()
        if not batch:
            return request.not_found()
        try:
            batch.check_access("read")
        except (AccessError, MissingError):
            return request.not_found()

        content = batch._get_xlsx_content()
        filename = "%s.xlsx" % batch.name.replace("/", "_")
        return request.make_response(
            content,
            headers=[
                (
                    "Content-Type",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                ("Content-Disposition", content_disposition(filename)),
            ],
        )
