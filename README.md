
# l10n_cr

Modulos de odoo para la Localización Costa Rica.

<!-- /!\ do not modify below this line -->

<!-- prettier-ignore-start -->

[//]: # (addons)

Addons disponibles
----------------
addon | version    | resumen
--- |------------| ---
[l10n_cr_address](l10n_cr_address/) | 18.0.1.0.0 | Topónimos de Costa Rica.
[l10n_cr_cabys](l10n_cr_cabys/) | 18.0.1.0.0 | Datos de CABYS para Comprobantes Electrónicos de Costa Rica.
[l10n_cr_currency_rate_live](l10n_cr_currency_rate_live/) | 18.0.1.0.0 | Tipo de cambio del BCCR.
[l10n_cr_invoice](l10n_cr_invoice/) | 18.0.1.0.0 | Factura electrónica Costa Rica.
[l10n_cr_invoice_pos](l10n_cr_invoice_pos/) | 18.0.1.0.0 | Factura electrónica Costa Rica - POS.
[l10n_cr_invoice_receptor](l10n_cr_invoice_receptor/) | 18.0.1.0.0 | Importa y Aceptar Facturas de Proveedor.
[l10n_cr_invoice_receptor_extract](l10n_cr_invoice_receptor_extract) | 18.0.1.0.0 | Extrae Facturas de Proveedor desde la bandeja de entrada del correo.
[l10n_cr_medical](l10n_cr_medical/) | 18.0.1.0.0 | Datos de uso para medicamentos de Comprobantes Electronicos de Costa Rica.
[l10n_cr_partner_autocomplete](l10n_cr_partner_autocomplete/) | 18.0.1.0.0 | Autocompletado de contactos por el NIT.
[l10n_cr_pos_sale](l10n_cr_pos_sale) | 18.0.1.0.0 | Modulo de enlace entre la POS-FE y Ventas.
[l10n_cr_reports](l10n_cr_reports/) | 18.0.1.0.0 | Reportes de declaraciones fiscales IVA.
[l10n_pos_invoice_print_without_download](l10n_pos_invoice_print_without_download/) | 18.0.1.0.0 | Crear facturas sin imprimir el PDF en POS.


[//]: # (end addons)

<!-- prettier-ignore-end -->

## Instalación

Para instalar los módulos de l10n_cr, vaya a Aplicaciones, luego elimine el filtro predeterminado «Aplicaciones» y
escriba l10n_cr.

----

## Factura electrónica

- Integración, gestión de certificado y firma digital.
- Envía al cliente por correo electrónico: Factura en PDF (Representación impresa), el XML generado y la respuesta del Ministerio de Hacienda.
- Gestión de Documentos Firmados.
- Sustituye factura rechazada por el Ministerio de Hacienda y hace referencia al documento actual rechazado.
- Autocompletado de contactos por el VAT.
- Múltiples exoneraciones por cliente

## Factura electrónica - POS

- Registro de Factura Electrónica, Tiquete Electrónico y Nota de Crédito Electrónica.
- Representacion impresa en formato ticket.
- Autocompletado de contactos por el VAT.
- Sustituye factura rechazada por el Ministerio de Hacienda y hace referencia al documento actual rechazado.
