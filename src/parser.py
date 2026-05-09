"""
Parser HTML optimizado para SICM usando Scrapling Selector
10x más rápido que regex puro
"""
from typing import Optional, List
import logging
from scrapling.parser import Selector

from src.models import Guia, Producto

logger = logging.getLogger(__name__)


def parse_guia_page(html: str, id_guia: int) -> Optional[Guia]:
    """
    Parser principal que extrae datos de una guía del SICM
    Usa Scrapling Selector para mejor rendimiento
    """
    try:
        # Crear selector Scrapling (10x más rápido que regex)
        selector = Selector(html)

        # Validar que el HTML contenga la guía solicitada
        nro_guia = selector.xpath(
            '//td[strong[contains(text(), "Nro Guia:")]]/following-sibling::td[1]/text()'
        ).get()

        if not nro_guia or int(nro_guia.strip()) != id_guia:
            logger.debug("guia_not_found", id=id_guia)
            return None

        # Extraer estatus y validar
        estatus = selector.xpath(
            '//td[strong[contains(text(), "Estatus:")]]/following-sibling::td[1]/text()'
        ).get()

        if not estatus or estatus.strip() not in ("APROBADA", "Abierta", "RECIBIDA"):
            logger.debug("invalid_estatus", id=id_guia, estatus=estatus)
            return None
        estatus = estatus.strip()

        # Extraer unidades y validar outliers
        unidades_str = selector.xpath(
            '//td[strong[contains(text(), "Unidades:")]]/following-sibling::td[1]/text()'
        ).get()

        unidades = 0
        if unidades_str:
            try:
                unidades = int(unidades_str.strip())
            except ValueError:
                pass

        if unidades > 1_000_000:
            logger.warning("outlier_detected", id=id_guia, unidades=unidades)
            return None

        # Extraer productos usando selector
        productos = _parse_productos(selector)

        # Construcción de modelo
        guia = Guia(
            id_guia=id_guia,
            estatus=estatus,
            fecha_emision=_extract_xpath(selector, "Fecha de Emisión"),
            fecha_vencimiento=_extract_xpath(selector, "Fecha de Vencimiento"),
            bultos=_extract_int(selector, "Bultos"),
            renglones=_extract_int(selector, "Renglones"),
            unidades=unidades,
            origen_razon=_extract_xpath(selector, "Origen - Razón"),
            origen_rif=_extract_xpath(selector, "Origen - RIF"),
            origen_tipo=_extract_xpath(selector, "Origen - Tipo"),
            origen_direccion=_extract_xpath(selector, "Origen - Dirección"),
            origen_estado_ciudad=_extract_xpath(selector, "Origen - Estado/Ciudad"),
            destino_razon=_extract_xpath(selector, "Destino - Razón"),
            destino_rif=_extract_xpath(selector, "Destino - RIF"),
            destino_tipo=_extract_xpath(selector, "Destino - Tipo"),
            destino_direccion=_extract_xpath(selector, "Destino - Dirección"),
            destino_estado_ciudad=_extract_xpath(selector, "Destino - Estado/Ciudad"),
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


def _extract_xpath(selector: Selector, field_name: str) -> Optional[str]:
    """Extrae campo usando XPath de Scrapling"""
    try:
        result = selector.xpath(
            f'//td[strong[contains(text(), "{field_name}:")]]/following-sibling::td[1]/text()'
        ).get()

        if result:
            # Limpiar espacios extras
            result = " ".join(result.split())
            return result if result else None
        return None
    except Exception:
        return None


def _extract_int(selector: Selector, field_name: str) -> Optional[int]:
    """Extrae campo como entero"""
    value = _extract_xpath(selector, field_name)
    if value:
        try:
            return int(value)
        except ValueError:
            pass
    return None


def _parse_productos(selector: Selector) -> List[Producto]:
    """
    Extrae la tabla de productos usando XPath de Scrapling
    """
    productos: List[Producto] = []

    try:
        # Buscar tabla de productos
        # XPath: encontrar tabla que contenga productos
        product_rows = selector.xpath(
            '//table[contains(@class, "productos") or .//td[contains(text(), "Producto")]]//tr[position() > 1]'
        )

        if not product_rows:
            # Fallback: buscar cualquier tabla con 3+ columnas
            product_rows = selector.xpath('//table[position() > 1]//tr[position() > 1]')

        for row in product_rows:
            try:
                # Extraer celdas
                cells = row.xpath('./td/text()').getall()

                if len(cells) < 3:
                    # Intentar con td[1], td[2], td[3]
                    cells = [
                        row.xpath('./td[1]/text()').get() or "",
                        row.xpath('./td[2]/text()').get() or "",
                        row.xpath('./td[3]/text()').get() or ""
                    ]

                if len(cells) < 3:
                    continue

                nombre = _clean_text(cells[0])
                lote = _clean_text(cells[1]) if len(cells) > 1 else None
                cantidad_str = _clean_text(cells[2]) if len(cells) > 2 else "0"

                # Validaciones
                if not nombre or nombre == "NO ESTA REGISTRADO EL PRODUCTO":
                    continue

                # Limpiar cantidad (solo números)
                cantidad_str = cantidad_str.replace(",", "").replace(".", "")
                try:
                    cantidad = int(cantidad_str)
                    if cantidad <= 0 or cantidad > 1_000_000:
                        continue

                    producto = Producto(nombre=nombre, lote=lote, cantidad=cantidad)
                    productos.append(producto)

                except (ValueError, TypeError):
                    continue

            except Exception as e:
                logger.debug("row_parse_error", error=str(e))
                continue

    except Exception as e:
        logger.debug("parse_productos_error", error=str(e))

    return productos


def _clean_text(text: Optional[str]) -> Optional[str]:
    """Limpia texto extraído"""
    if not text:
        return None

    text = text.strip()
    text = " ".join(text.split())

    return text if text else None