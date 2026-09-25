import io
import math

from odoo import models
from odoo.tools.pdf import PdfFileReader, PdfFileWriter


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @staticmethod
    def _custom_label_page_count(data):
        quantity = sum((data.get("quantity_by_product") or {}).values())
        quantity += sum(
            barcode_quantity
            for barcode_quantities in (data.get("custom_barcodes") or {}).values()
            for _barcode, barcode_quantity in barcode_quantities
        )
        labels_per_page = data.get("custom_label_rows", 1) * data.get(
            "custom_label_columns", 1
        )
        return math.ceil(quantity / labels_per_page) if labels_per_page else 0

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        pdf_content, report_type = super()._render_qweb_pdf(
            report_ref, res_ids=res_ids, data=data
        )
        report = self._get_report(report_ref)
        if (
            report_type == "pdf"
            and report.report_name
            == "indoor_inventario.report_producttemplatelabel_custom"
        ):
            expected_pages = self._custom_label_page_count(data or {})
            reader = PdfFileReader(io.BytesIO(pdf_content), strict=False)
            if expected_pages and reader.getNumPages() > expected_pages:
                writer = PdfFileWriter()
                for page_number in range(expected_pages):
                    writer.addPage(reader.getPage(page_number))
                with io.BytesIO() as output:
                    writer.write(output)
                    pdf_content = output.getvalue()
        return pdf_content, report_type


class ReportProductTemplateLabelCustom(models.AbstractModel):
    _name = "report.indoor_inventario.report_producttemplatelabel_custom"
    _inherit = "report.product.report_producttemplatelabel_dymo"
    _description = "Reporte de etiquetas de producto personalizadas"

    def _get_report_values(self, docids, data):
        values = super()._get_report_values(docids, data)
        width = data.get("custom_label_width", 50.0)
        height = data.get("custom_label_height", 30.0)
        columns = data.get("custom_label_columns", 1)
        rows = data.get("custom_label_rows", 1)
        gap = 5.0
        barcode_width = max(width - 40.0, 10.0)
        label_inner_height = max(height - 3.0, 1.0)
        barcode_height = min(max(height * 0.25, 3.0), label_inner_height)
        barcode_top = max((label_inner_height - barcode_height) / 2.0, 0.0)
        label_vertical_gap = max(min(height * 0.05, 8.0), 2.0)
        values.update(
            custom_label_width=width,
            custom_label_height=height,
            columns=columns,
            rows=rows,
            grid_width=columns * width + (columns - 1) * gap,
            grid_height=rows * height + (rows - 1) * gap,
            label_gap=gap,
            barcode_width=barcode_width,
            barcode_height=barcode_height,
            barcode_top=barcode_top,
            label_text_offset=barcode_top + barcode_height + label_vertical_gap,
            label_text_zone_height=max(barcode_top - label_vertical_gap, 1.0),
            label_name_font_size=max(min(height * 0.16, 18.0), 8.0),
            barcode_text_font_size=max(min(height * 0.11, 14.0), 8.0),
        )
        return values
