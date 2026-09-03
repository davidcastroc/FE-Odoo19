===============
Invoice Receptor
===============


<!-- prettier-ignore-end -->

## Características

Puede activar la Extracción automática solo de archivos XML, para ello busque el diario que recibe correos 
electrónicos y en la pestaña Ajustes Avanzados active el ckeck..

----


- Solo se permite la creación de facturas que contengan adjunto al menos un XML.
- No permite crear facturas con un mismo consecutivo.

## Ejemplo

- Un correo con los siguientes adjunto: XML de FE, el pdf y la RH (Respuesta de Hacienda) será creada la factura.
- Un correo con un solo adjunto qu sea por ejemplo un pdf, img, etc. No se crea la factura..
- Un correo q contenga un solo adjunto que sea un XML de FE será creada la factura.
- Un correo con un solo adjunto y que sea un xml de RH y que pertenezca a una factura previamente creada con ese consecutivo entonces lo adjunta a ella. Un correo con un solo adjunto y q sea un xml de RH y que no exista a una factura previamente creada con ese consecutivo entonces no se crea la factura. Todo esto porque a veces los proveedores envían el XML y al rato la RH.
- Un correo con un solo adjunto que se aun XML de un TE (Tiquete Electrónico), no se crea la factura.