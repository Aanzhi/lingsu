import binascii
import logging
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import transaction

from .models import PlatformAIConfiguration


logger = logging.getLogger(__name__)
DEFAULT_CONFIG_KEY = "default"
MAX_MODEL_LENGTH = 128
MAX_BASE_URL_LENGTH = 512


class AIConfigError(Exception):
    """Raised when the deployment cannot encrypt or decrypt the platform AI Key."""


class AIConfigValidationError(ValueError):
    """Raised when a platform AI provider field is invalid."""

    def __init__(self, field, message):
        self.field = field
        super().__init__(message)


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


def _effective_model(record=None):
    record = record if record is not None else _record()
    value = getattr(record, "model", "") if record is not None else ""
    return str(value or getattr(settings, "OPENAI_MODEL", "") or "").strip()


def _effective_base_url(record=None):
    record = record if record is not None else _record()
    value = getattr(record, "base_url", "") if record is not None else ""
    return str(value or getattr(settings, "OPENAI_BASE_URL", "") or "").strip()


def _decrypt_record_key(record):
    if not record or not record.encrypted_api_key:
        return ""
    try:
        return _fernet().decrypt(record.encrypted_api_key.encode("utf-8")).decode("utf-8")
    except (AIConfigError, InvalidToken, UnicodeDecodeError, ValueError) as exc:
        logger.error("平台 AI Key 无法解密，已按未配置处理：%s", type(exc).__name__)
        return ""


def get_ai_configuration_state():
    record = _record()
    if record:
        return {
            "configured": bool(record.encrypted_api_key or record.masked_api_key),
            "masked_key": record.masked_api_key,
            "model": _effective_model(record),
            "base_url": _effective_base_url(record),
        }
    fallback = str(getattr(settings, "OPENAI_API_KEY", "") or "")
    return {
        "configured": bool(fallback),
        "masked_key": mask_ai_api_key(fallback),
        "model": _effective_model(),
        "base_url": _effective_base_url(),
    }


def get_configured_ai_runtime():
    """Return effective provider settings for server-side AI calls only."""
    record = _record()
    if record:
        return {
            "api_key": _decrypt_record_key(record),
            "model": _effective_model(record),
            "base_url": _effective_base_url(record),
        }
    return {
        "api_key": str(getattr(settings, "OPENAI_API_KEY", "") or ""),
        "model": _effective_model(),
        "base_url": _effective_base_url(),
    }


def get_configured_ai_api_key():
    return get_configured_ai_runtime()["api_key"]


def _validate_provider_fields(model, base_url, allow_empty_base_url=False):
    model = str(model or "").strip()
    base_url = str(base_url or "").strip()
    if not model:
        raise AIConfigValidationError("model", "模型名称不能为空。")
    if len(model) > MAX_MODEL_LENGTH:
        raise AIConfigValidationError("model", "模型名称长度超过允许范围。")
    if not base_url and allow_empty_base_url:
        return model, base_url
    if not base_url:
        raise AIConfigValidationError("base_url", "Base URL 不能为空。")
    if len(base_url) > MAX_BASE_URL_LENGTH:
        raise AIConfigValidationError("base_url", "Base URL 长度超过允许范围。")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise AIConfigValidationError("base_url", "Base URL 必须是有效的 HTTP(S) 地址。")
    return model, base_url


def save_platform_ai_configuration(api_key, model, base_url, actor):
    model, base_url = _validate_provider_fields(model, base_url)
    api_key = str(api_key or "").strip()
    record = _record()
    if not record and not api_key:
        api_key = str(getattr(settings, "OPENAI_API_KEY", "") or "").strip()
        if not api_key:
            raise AIConfigValidationError("api_key", "首次配置必须输入 API Key。")
    if len(api_key) > 4096:
        raise AIConfigValidationError("api_key", "API Key 长度超过允许范围。")
    encrypted = _fernet().encrypt(api_key.encode("utf-8")).decode("utf-8") if api_key else ""
    with transaction.atomic():
        record, _ = PlatformAIConfiguration.objects.select_for_update().get_or_create(key=DEFAULT_CONFIG_KEY)
        if api_key:
            record.encrypted_api_key = encrypted
            record.masked_api_key = mask_ai_api_key(api_key)
        record.model = model
        record.base_url = base_url
        record.updated_by = actor
        update_fields = ["model", "base_url", "updated_by", "updated_at"]
        if api_key:
            update_fields.extend(["encrypted_api_key", "masked_api_key"])
        record.save(update_fields=update_fields)
    return get_ai_configuration_state()


def save_configured_ai_api_key(value, actor):
    """Backward-compatible Key-only writer for existing server-side callers."""
    value = str(value or "").strip()
    if not value:
        raise ValueError("API Key 不能为空。")
    if len(value) > 4096:
        raise ValueError("API Key 长度超过允许范围。")
    model, base_url = _validate_provider_fields(_effective_model(), _effective_base_url(), allow_empty_base_url=True)
    encrypted = _fernet().encrypt(value.encode("utf-8")).decode("utf-8")
    with transaction.atomic():
        record, _ = PlatformAIConfiguration.objects.select_for_update().get_or_create(key=DEFAULT_CONFIG_KEY)
        record.encrypted_api_key = encrypted
        record.masked_api_key = mask_ai_api_key(value)
        record.model = model
        record.base_url = base_url
        record.updated_by = actor
        record.save(update_fields=["encrypted_api_key", "masked_api_key", "model", "base_url", "updated_by", "updated_at"])
    return get_ai_configuration_state()
