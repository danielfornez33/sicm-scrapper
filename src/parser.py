"""
Parser HTML optimizado para SICM
Extrae guías de transporte del sitio www.sicm.gob.ve
"""

from typing import Optional, List
import logging
import re
from src.models import Guia, Producto

logger = logging.getLogger(__name__)


def parse_guia_page(html: str, id_guia: int) -> Optional[Guia]:
    """
    Parser principal que extrae datos de una guía del SICM

    El HTML sigue un patrón de tabla con:
    <td><strong>Campo:</strong></td><td>VALOR</td>
    """
    try:
        # Validar que el HTML contenga la guía solicitada
        if f"Nro Guia:</strong></td><td>{id_guia}" not in html:
            logger.debug("guia_not_found", id=id_guia)
            return None

        # Extraer campos principales
        nro_guia = _extract_field(html, "Nro Guia")
        if not nro_guia or int(nro_guia) != id_guia:
            return None

        estatus = _extract_field(html, "Estatus")
        if not estatus or estatus not in ("APROBADA", "Abierta", "RECIBIDA"):
            logger.debug("invalid_estatus", id=id_guia, estatus=estatus)
            return None

        # Validar outliers antes de continuar
        unidades_str = _extract_field(html, "Unidades")
        unidades = int(unidades_str) if unidades_str else 0
        if unidades > 1_000_000:
            logger.warning("outlier_detected", id=id_guia, unidades=unidades)
            return None

        # Extraer productos
        productos = _parse_productos(html)

        # Construcción de modelo
        guia = Guia(
            id_guia=id_guia,
            estatus=estatus,
            fecha_emision=_extract_field(html, "Fecha de Emisión"),
            fecha_vencimiento=_extract_field(html, "Fecha de Vencimiento"),
            bultos=int(b) if (b := _extract_field(html, "Bultos")) else None,
            renglones=int(r) if (r := _extract_field(html, "Renglones")) else None,
            unidades=unidades,
            origen_razon=_extract_field(html, "Origen - Razón"),
            origen_rif=_extract_field(html, "Origen - RIF"),
            origen_tipo=_extract_field(html, "Origen - Tipo"),
            origen_direccion=_extract_field(html, "Origen - Dirección"),
            origen_estado_ciudad=_extract_field(html, "Origen - Estado/Ciudad"),
            destino_razon=_extract_field(html, "Destino - Razón"),
            destino_rif=_extract_field(html, "Destino - RIF"),
            destino_tipo=_extract_field(html, "Destino - Tipo"),
            destino_direccion=_extract_field(html, "Destino - Dirección"),
            destino_estado_ciudad=_extract_field(html, "Destino - Estado/Ciudad"),
            productos=productos,
        )

        logger.debug("guia_parsed", id=id_guia, productos=len(productos))
        return guia

    except ValueError as e:
        logger.warning("guia_parse_error", id=id_guia, error=str(e))
        return None
    except Exception as e:
        logger.error("guia_parse_exception", id=id_guia, error=str(e))
        return None


def _extract_field(html: str, field_name: str) -> Optional[str]:
    """
    Extrae un campo de valor del patrón HTML:
    <td><strong>Campo:</strong></td><td>VALOR</td>
    """
    # Búsqueda robusta del patrón
    pattern = rf"<strong>{re.escape(field_name)}:\s*</strong>\s*</td>\s*<td>\s*([^<]+)"
    match = re.search(pattern, html, re.IGNORECASE)

    if match:
        value = match.group(1).strip()
        # Limpiar HTML entities y espacios extras
        value = value.replace("&nbsp;", " ").replace("&amp;", "&")
        value = re.sub(r"\s+", " ", value)
        return value if value else None

    return None


def _parse_productos(html: str) -> List[Producto]:
    """
    Extrae la tabla de productos
    Asume una estructura similar a:
    <tr><td>PRODUCTO</td><td>LOTE</td><td>CANTIDAD</td></tr>
    """
    productos: List[Producto] = []

    # Buscar la tabla de productos (puede estar en diferentes formatos)
    table_match = re.search(r"<table[^>]*>.*?</table>", html, re.IGNORECASE | re.DOTALL)
    if not table_match:
        return productos

    table_html = table_match.group(0)

    # Extraer filas de datos (saltando encabezados)
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, re.IGNORECASE | re.DOTALL)

    for i, row in enumerate(rows[1:]):  # Skip header row
        try:
            # Extraer celdas
            cells = re.findall(r"<td[^>]*>\s*(.*?)\s*</td>", row, re.IGNORECASE | re.DOTALL)

            if len(cells) < 3:
                continue

            nombre = _clean_text(cells[0])
            lote = _clean_text(cells[1]) if len(cells) > 1 else None
            cantidad_str = _clean_text(cells[2]) if len(cells) > 2 else "0"

            # Validaciones
            if not nombre or nombre == "NO ESTA REGISTRADO EL PRODUCTO":
                continue

            try:
                cantidad = int(re.sub(r"[^\d]", "", cantidad_str))
                if cantidad <= 0 or cantidad > 1_000_000:
                    continue

                producto = Producto(nombre=nombre, lote=lote, cantidad=cantidad)
                productos.append(producto)

            except (ValueError, TypeError):
                logger.debug("invalid_cantidad", row_idx=i, cantidad=cantidad_str)
                continue

        except Exception as e:
            logger.debug("row_parse_error", row_idx=i, error=str(e))
            continue

    return productos


def _clean_text(html_text: str) -> Optional[str]:
    """
    Limpia texto HTML:
    - Elimina tags HTML
    - Elimina entities HTML
    - Trim de espacios
    """
    if not html_text:
        return None

    # Eliminar tags HTML
    text = re.sub(r"<[^>]+>", "", html_text)

    # Eliminar entities HTML comunes
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')

    # Normalizar espacios
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text if text else None
