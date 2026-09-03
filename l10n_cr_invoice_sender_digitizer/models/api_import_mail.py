# -*- coding: utf-8 -*-

import zipfile
import io
import logging
_logger = logging.getLogger(__name__)

AVAILABLE_VOUCHER_TYPES = ["FacturaElectronica", "NotaCreditoElectronica", "NotaDebitoElectronica", "MensajeHacienda"]


def l10n_cr_get_attachment_zip(zip_bytes):
    """Get the attachment of the invoice"""

    # Crear un archivo en memoria desde los bytes
    zip_stream = io.BytesIO(zip_bytes)

    with zipfile.ZipFile(zip_stream, 'r') as zip_ref:
        for file_name in zip_ref.namelist():
            with zip_ref.open(file_name) as file:
                # type_file = file_name.split(".")[1]
                type_file = file_name.split(".")[1] if len(file_name.split(".")) > 1 else ''
                content = file.read()  # contenido es de tipo bytes
                _logger.info(f"{file_name}: {len(content)} bytes")
                if type_file.upper() == "XML":
                    return content
