import binascii
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import transaction

from .models import PlatformAIConfiguration


logger = logging.getLogger(__name__)
DEFAULT_CONFIG_KEY = "default"


class AIConfigError(Exception):
    """Raised when the deployment cannot encrypt or decrypt the platform AI Key."""


def mask_ai_api_key(value):
    value = str(value or "")
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * 8
    return f"{value[:4]}{'*' * 8}{value[-4:]}"


def _fernet():
    raw_key = str(getattr(settings, "AI_CONFIG_ENCRYPTION_KEY", "") or "").strip()
    if not raw_key:
        raise AIConfigError("未配置 AI 配置加密密钥。")
    try:
        return Fernet(raw_key.encode("ascii"))
    except (ValueError, TypeError, UnicodeEncodeError, binascii.Error) as exc:
        raise AIConfigError("AI 配置加密密钥格式无效。") from exc


def _record():
    return PlatformAIConfiguration.objects.filter(key=DEFAULT_CONFIG_KEY).first()


def get_ai_configuration_state():
    record = _record()
    if record:
        return {"configured": True, "masked_key": record.masked_api_key}
    fallback = str(getattr(settings, "OPENAI_API_KEY", "") or "")
    return {"configured": bool(fallback), "masked_key": mask_ai_api_key(fallback)}


def get_configured_ai_api_key():
    record = _record()
    if record:
        try:
            return _fernet().decrypt(record.encrypted_api_key.encode("utf-8")).decode("utf-8")
        except (AIConfigError, InvalidToken, UnicodeDecodeError, ValueError) as exc:
            logger.error("平台 AI Key 无法解密，已按未配置处理：%s", type(exc).__name__)
            return ""
    return str(getattr(settings, "OPENAI_API_KEY", "") or "")


def save_configured_ai_api_key(value, actor):
    value = str(value or "").strip()
    if not value:
        raise ValueError("API Key 不能为空。")
    if len(value) > 4096:
        raise ValueError("API Key 长度超过允许范围。")
    encrypted = _fernet().encrypt(value.encode("utf-8")).decode("utf-8")
    with transaction.atomic():
        record, _ = PlatformAIConfiguration.objects.select_for_update().get_or_create(key=DEFAULT_CONFIG_KEY)
        record.encrypted_api_key = encrypted
        record.masked_api_key = mask_ai_api_key(value)
        record.updated_by = actor
        record.save(update_fields=["encrypted_api_key", "masked_api_key", "updated_by", "updated_at"])
    return get_ai_configuration_state()
