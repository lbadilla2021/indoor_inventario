from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError


class InventoryCountSession(models.Model):
    _name = "indoor.inventory.count.session"
    _description = "Sesión de Inventario"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Referencia",
        default=lambda self: _("Nuevo"),
        copy=False,
        readonly=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("in_progress", "En proceso"),
            ("in_review", "En revisión"),
            ("closed", "Cerrado"),
            ("cancelled", "Cancelado"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
    )
    location_id = fields.Many2one(
        "stock.location",
        string="Ubicación",
        required=True,
        domain="[('usage', '=', 'internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        default=lambda self: self._default_location_id(),
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    responsible_id = fields.Many2one(
        "res.users",
        string="Responsable",
        default=lambda self: self.env.user,
        tracking=True,
    )
    start_date = fields.Datetime(string="Inicio", readonly=True)
    review_date = fields.Datetime(string="En revisión desde", readonly=True)
    prepared_date = fields.Datetime(string="Inventario físico preparado", readonly=True)
    prepared_by_id = fields.Many2one("res.users", string="Preparado por", readonly=True)
    prepared_quant_count = fields.Integer(
        string="Líneas preparadas", readonly=True, copy=False
    )
    close_date = fields.Datetime(string="Cierre", readonly=True)
    line_ids = fields.One2many(
        "indoor.inventory.count.line", "session_id", string="Líneas de conteo"
    )
    line_count = fields.Integer(string="Lecturas", compute="_compute_line_count")
    product_count = fields.Integer(string="Productos", compute="_compute_line_count")
    last_scan_date = fields.Datetime(
        string="Última lectura", compute="_compute_line_count"
    )
    last_scan_user_id = fields.Many2one(
        "res.users", string="Último usuario", compute="_compute_line_count"
    )
    note = fields.Text(string="Nota")

    @api.model
    def _default_location_id(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        return warehouse.lot_stock_id.id if warehouse else False

    @api.depends("line_ids", "line_ids.product_id")
    def _compute_line_count(self):
        for session in self:
            session.line_count = len(session.line_ids)
            session.product_count = len(session.line_ids.mapped("product_id"))
            last_line = session.line_ids.sorted(
                key=lambda line: (line.scan_date, line.id), reverse=True
            )[:1]
            session.last_scan_date = last_line.scan_date
            session.last_scan_user_id = last_line.scan_user_id

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = sequence.next_by_code(
                    "indoor.inventory.count.session"
                ) or _("Nuevo")
        return super().create(vals_list)

    def action_start(self):
        for session in self.filtered(lambda record: record.state == "draft"):
            session.write(
                {"state": "in_progress", "start_date": fields.Datetime.now()}
            )
        return True

    def action_send_to_review(self):
        for session in self.filtered(
            lambda record: record.state in ("draft", "in_progress")
        ):
            session.write(
                {"state": "in_review", "review_date": fields.Datetime.now()}
            )
        return True

    def action_close(self):
        for session in self:
            if session.state != "in_review":
                raise UserError(_("Solo se pueden cerrar sesiones en revisión."))
            if not session.prepared_date:
                raise UserError(
                    _("Debe preparar el inventario físico antes de cerrar la sesión.")
                )
            session.write(
                {"state": "closed", "close_date": fields.Datetime.now()}
            )
        return True

    def action_cancel(self):
        self.write({"state": "cancelled"})
        return True

    def action_prepare_physical_inventory(self):
        self.ensure_one()
        if not self.env.user.has_group("stock.group_stock_manager"):
            raise UserError(
                _(
                    "Solo un administrador de inventario puede preparar el inventario físico."
                )
            )
        if self.state != "in_review":
            raise UserError(
                _(
                    "Solo se puede preparar inventario físico desde una sesión en revisión."
                )
            )
        if not self.line_ids:
            raise UserError(_("La sesión no tiene lecturas para preparar."))

        self.env["indoor.inventory.count.line"].flush_model()
        consolidated_lines = self.env[
            "indoor.inventory.count.consolidated"
        ].search([("session_id", "=", self.id)])
        if not consolidated_lines:
            raise UserError(_("No existen cantidades consolidadas para esta sesión."))

        Quant = self.env["stock.quant"].with_context(inventory_mode=True)
        prepared_quants = self.env["stock.quant"]
        for line in consolidated_lines:
            quant_domain = [
                ("product_id", "=", line.product_id.id),
                ("location_id", "=", line.location_id.id),
                ("lot_id", "=", line.lot_id.id if line.lot_id else False),
                ("package_id", "=", False),
                ("owner_id", "=", False),
                "|",
                ("company_id", "=", line.company_id.id),
                ("company_id", "=", False),
            ]
            quant = Quant.search(quant_domain, limit=1)
            values = {
                "inventory_quantity": line.counted_quantity,
                "user_id": self.env.user.id,
                "inventory_date": fields.Date.today(),
            }
            if quant:
                quant.write(values)
            else:
                values.update(
                    {
                        "product_id": line.product_id.id,
                        "location_id": line.location_id.id,
                        "lot_id": line.lot_id.id if line.lot_id else False,
                    }
                )
                quant = Quant.create(values)
            prepared_quants |= quant

        self.write(
            {
                "prepared_date": fields.Datetime.now(),
                "prepared_by_id": self.env.user.id,
                "prepared_quant_count": len(prepared_quants),
            }
        )
        self.message_post(
            body=_(
                "Inventario físico preparado con %s línea(s). Revise y aplique el ajuste desde Inventario."
            )
            % len(prepared_quants)
        )
        return self._action_open_prepared_inventory(prepared_quants)

    def _action_open_prepared_inventory(self, quants):
        action = {
            "type": "ir.actions.act_window",
            "name": _("Inventario físico preparado"),
            "res_model": "stock.quant",
            "view_mode": "list",
            "domain": [("id", "in", quants.ids)],
            "context": {
                "inventory_mode": True,
                "search_default_to_apply": 1,
                "search_default_internal_loc": 1,
            },
        }
        editable_view = self.env.ref(
            "stock.view_stock_quant_tree_editable", raise_if_not_found=False
        )
        if editable_view:
            action["views"] = [(editable_view.id, "list")]
        return action

    @api.model
    def _migrate_from_ziv_cod_barra(self):
        """Copy legacy sessions into Indoor-owned tables and move their chatter."""
        self.env.cr.execute("SELECT to_regclass('ziv_inventory_count_session')")
        if not self.env.cr.fetchone()[0]:
            return True

        self.env.cr.execute(
            """
            INSERT INTO indoor_inventory_count_session (
                id, location_id, company_id, responsible_id, prepared_by_id,
                prepared_quant_count, create_uid, write_uid, name, state, note,
                start_date, review_date, prepared_date, close_date, create_date,
                write_date
            )
            SELECT
                id, location_id, company_id, responsible_id, prepared_by_id,
                prepared_quant_count, create_uid, write_uid, name, state, note,
                start_date, review_date, prepared_date, close_date, create_date,
                write_date
            FROM ziv_inventory_count_session
            ON CONFLICT (id) DO NOTHING
            """
        )
        self.env.cr.execute("SELECT to_regclass('ziv_inventory_count_line')")
        if self.env.cr.fetchone()[0]:
            self.env.cr.execute(
                """
                INSERT INTO indoor_inventory_count_line (
                    id, session_id, product_id, product_uom_id, company_id,
                    location_id, lot_id, scan_user_id, create_uid, write_uid,
                    state, barcode, note, quantity, scan_date, create_date,
                    write_date
                )
                SELECT
                    id, session_id, product_id, product_uom_id, company_id,
                    location_id, lot_id, scan_user_id, create_uid, write_uid,
                    state, barcode, note, quantity, scan_date, create_date,
                    write_date
                FROM ziv_inventory_count_line
                ON CONFLICT (id) DO NOTHING
                """
            )

        for table in (
            "indoor_inventory_count_session",
            "indoor_inventory_count_line",
        ):
            self.env.cr.execute(
                "SELECT setval(pg_get_serial_sequence(%s, 'id'), "
                "GREATEST(COALESCE((SELECT MAX(id) FROM %s), 1), 1), true)"
                % ("%s", table),
                [table],
            )

        old_sequence = self.env["ir.sequence"].sudo().search(
            [("code", "=", "ziv.inventory.count.session")], limit=1
        )
        new_sequence = self.env.ref(
            "indoor_inventario.seq_inventory_count_session",
            raise_if_not_found=False,
        )
        if old_sequence and new_sequence:
            new_sequence.sudo().number_next_actual = max(
                old_sequence.number_next_actual, new_sequence.number_next_actual
            )

        migrated_ids = self.sudo().search([]).ids
        if migrated_ids:
            for table, model_column in (
                ("mail_message", "model"),
                ("mail_followers", "res_model"),
                ("mail_activity", "res_model"),
                ("ir_attachment", "res_model"),
            ):
                self.env.cr.execute(
                    "SELECT to_regclass(%s)", [table]
                )
                if self.env.cr.fetchone()[0]:
                    self.env.cr.execute(
                        f"UPDATE {table} SET {model_column} = %s "
                        f"WHERE {model_column} = %s AND res_id = ANY(%s)",
                        [
                            "indoor.inventory.count.session",
                            "ziv.inventory.count.session",
                            migrated_ids,
                        ],
                    )

        legacy_menu = self.env.ref(
            "ziv_cod_barra.menu_ziv_stock_barcode_root", raise_if_not_found=False
        )
        if legacy_menu:
            legacy_menu.sudo().active = False
        return True


class InventoryCountLine(models.Model):
    _name = "indoor.inventory.count.line"
    _description = "Línea de Conteo de Inventario"
    _order = "scan_date desc, id desc"

    session_id = fields.Many2one(
        "indoor.inventory.count.session",
        string="Sesión",
        required=True,
        ondelete="cascade",
        default=lambda self: self._default_session_id(),
    )
    state = fields.Selection(related="session_id.state", string="Estado", store=True)
    barcode = fields.Char(
        string="Código de barra",
        help="Escanee el código de barra con el cursor en este campo.",
    )
    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        domain=[("is_storable", "=", True)],
        required=True,
    )
    quantity = fields.Float(
        string="Cantidad contada",
        required=True,
        default=1.0,
        digits="Product Unit of Measure",
    )
    product_uom_id = fields.Many2one(
        "uom.uom",
        string="Unidad",
        related="product_id.uom_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        related="session_id.company_id",
        store=True,
        readonly=True,
    )
    location_id = fields.Many2one(
        "stock.location",
        string="Ubicación",
        required=True,
        domain="[('usage', '=', 'internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        default=lambda self: self._default_location_id(),
    )
    lot_id = fields.Many2one(
        "stock.lot",
        string="Lote/Serie",
        domain="[('product_id', '=', product_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    tracking = fields.Selection(related="product_id.tracking", readonly=True)
    scan_user_id = fields.Many2one(
        "res.users", string="Usuario", default=lambda self: self.env.user, readonly=True
    )
    scan_date = fields.Datetime(
        string="Fecha lectura", default=fields.Datetime.now, readonly=True
    )
    note = fields.Char(string="Nota")

    @api.model
    def _default_session_id(self):
        session = self.env["indoor.inventory.count.session"].search(
            [
                ("state", "in", ("draft", "in_progress")),
                ("responsible_id", "=", self.env.user.id),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        if session:
            return session.id
        return self.env["indoor.inventory.count.session"].create({}).id

    @api.model
    def _default_location_id(self):
        session_id = self.env.context.get("default_session_id")
        if session_id:
            session = self.env["indoor.inventory.count.session"].browse(session_id)
            if session.exists() and session.location_id:
                return session.location_id.id
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        return warehouse.lot_stock_id.id if warehouse else False

    @api.constrains("quantity")
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_("La cantidad debe ser mayor que cero."))

    @api.constrains("session_id")
    def _check_session_open(self):
        for line in self:
            if line.session_id.state not in ("draft", "in_progress"):
                raise ValidationError(
                    _(
                        "Solo se pueden registrar lecturas en sesiones en borrador o en proceso."
                    )
                )

    @api.constrains("product_id", "lot_id")
    def _check_tracking_lot(self):
        for line in self:
            if line.product_id.tracking != "none" and not line.lot_id:
                raise ValidationError(
                    _("Debe indicar un lote o serie para el producto %s.")
                    % line.product_id.display_name
                )

    @api.onchange("session_id")
    def _onchange_session_id(self):
        for line in self:
            if line.session_id:
                line.location_id = line.session_id.location_id

    @api.onchange("barcode")
    def _onchange_barcode(self):
        for line in self:
            if not line.barcode:
                continue
            product = self.env["product.product"].search(
                [("barcode", "=", line.barcode.strip())], limit=2
            )
            if len(product) == 1:
                line.product_id = product
                line.lot_id = False
                if not line.quantity:
                    line.quantity = 1.0
            elif product:
                return {
                    "warning": {
                        "title": _("Código duplicado"),
                        "message": _(
                            "Existe más de un producto con el código de barra %s."
                        )
                        % line.barcode,
                    }
                }
            else:
                return {
                    "warning": {
                        "title": _("Producto no encontrado"),
                        "message": _(
                            "No se encontró ningún producto con el código de barra %s."
                        )
                        % line.barcode,
                    }
                }
        return None

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.barcode = line.product_id.barcode or line.barcode
                line.lot_id = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.session_id.filtered(
            lambda session: session.state == "draft"
        ).action_start()
        return records

    def write(self, vals):
        if any(
            line.session_id.state not in ("draft", "in_progress") for line in self
        ):
            raise UserError(
                _(
                    "Solo se pueden modificar lecturas en sesiones en borrador o en proceso."
                )
            )
        return super().write(vals)


class InventoryCountConsolidated(models.Model):
    _name = "indoor.inventory.count.consolidated"
    _description = "Consolidado de Inventario"
    _auto = False
    _order = "session_id desc, product_id"

    session_id = fields.Many2one(
        "indoor.inventory.count.session", string="Sesión", readonly=True
    )
    company_id = fields.Many2one("res.company", string="Compañía", readonly=True)
    location_id = fields.Many2one("stock.location", string="Ubicación", readonly=True)
    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    product_uom_id = fields.Many2one("uom.uom", string="Unidad", readonly=True)
    lot_id = fields.Many2one("stock.lot", string="Lote/Serie", readonly=True)
    counted_quantity = fields.Float(
        string="Cantidad contada", readonly=True, digits="Product Unit of Measure"
    )
    current_quantity = fields.Float(
        string="Cantidad actual", readonly=True, digits="Product Unit of Measure"
    )
    difference_quantity = fields.Float(
        string="Diferencia", readonly=True, digits="Product Unit of Measure"
    )
    scan_count = fields.Integer(string="Lecturas", readonly=True)
    user_count = fields.Integer(string="Usuarios", readonly=True)
    last_scan_date = fields.Datetime(string="Última lectura", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    grouped.id,
                    grouped.session_id,
                    grouped.company_id,
                    grouped.location_id,
                    grouped.product_id,
                    grouped.product_uom_id,
                    grouped.lot_id,
                    grouped.counted_quantity,
                    COALESCE(quant.current_quantity, 0.0) AS current_quantity,
                    grouped.counted_quantity - COALESCE(quant.current_quantity, 0.0) AS difference_quantity,
                    grouped.scan_count,
                    grouped.user_count,
                    grouped.last_scan_date
                FROM (
                    SELECT
                        MIN(line.id) AS id,
                        line.session_id,
                        line.company_id,
                        line.location_id,
                        line.product_id,
                        line.product_uom_id,
                        line.lot_id,
                        SUM(line.quantity) AS counted_quantity,
                        COUNT(line.id) AS scan_count,
                        COUNT(DISTINCT line.scan_user_id) AS user_count,
                        MAX(line.scan_date) AS last_scan_date
                    FROM indoor_inventory_count_line line
                    GROUP BY
                        line.session_id,
                        line.company_id,
                        line.location_id,
                        line.product_id,
                        line.product_uom_id,
                        line.lot_id
                ) grouped
                LEFT JOIN LATERAL (
                    SELECT SUM(quant.quantity) AS current_quantity
                    FROM stock_quant quant
                    WHERE quant.product_id = grouped.product_id
                        AND quant.location_id = grouped.location_id
                        AND COALESCE(quant.lot_id, 0) = COALESCE(grouped.lot_id, 0)
                        AND quant.package_id IS NULL
                        AND quant.owner_id IS NULL
                        AND (quant.company_id = grouped.company_id OR quant.company_id IS NULL)
                ) quant ON TRUE
            )
            """
            % self._table
        )
