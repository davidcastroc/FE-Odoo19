# Costa Rica - Consulta de Contribuyentes MH (Odoo 18)

Módulo independiente para consultar un contacto en el API público del Ministerio de Hacienda de Costa Rica.

## Uso
1. Instalar el módulo.
2. Abrir un contacto.
3. Colocar la cédula/identificación en el campo estándar **Referencia** (`res.partner.ref`).
4. Pulsar **Consultar en MH**.
5. Se abre un asistente con la información devuelta por Hacienda.

## Dependencias
- `base`
- `contacts`
- Python `requests`

No depende del módulo `cr_electronic_invoice`.
