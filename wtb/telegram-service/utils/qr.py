import logging
import qrcode
from io import BytesIO
from core.settings import logger

# Генерация QR-кода для конфигурации
async def generate_config_qr(config_text):
    """Генерирует QR-код на основе текста конфигурации."""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(config_text)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        
        return buf
    except Exception as e:
        logger.error(f"Ошибка при генерации QR-кода: {str(e)}")
        return None