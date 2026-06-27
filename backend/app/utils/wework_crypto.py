"""企微消息加解密工具

实现企微"接收消息"回调的加解密协议：
- URL验证（GET）：校验签名 + 解密 echostr 返回明文
- 事件推送（POST）：校验签名 + 解密 XML 消息体

参考: https://developer.work.weixin.qq.com/document/path/90930
"""
import base64
import hashlib
import socket
import struct
import time
import xml.etree.ElementTree as ET
from Crypto.Cipher import AES

from app.config import get_settings


def _get_aes_key() -> bytes:
    """从配置读取 EncodingAESKey 并 base64 解码为 32 字节密钥。"""
    key = get_settings().WECOM_CALLBACK_AES_KEY
    if not key or len(key) != 43:
        raise ValueError(f"WECOM_CALLBACK_AES_KEY 必须是 43 字符的 Base64 字符串，当前: {len(key) if key else 0}")
    # 企微规范: EncodingAESKey + "=" 再 base64 解码得到 32 字节 AES 密钥
    return base64.b64decode(key + "=")


def _sha1_signature(token: str, timestamp: str, nonce: str, encrypt: str = "") -> str:
    """企微签名: sha1(sort([token, timestamp, nonce, encrypt]))."""
    if encrypt:
        parts = sorted([token, timestamp, nonce, encrypt])
    else:
        parts = sorted([token, timestamp, nonce])
    raw = "".join(parts).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def verify_signature(msg_signature: str, token: str, timestamp: str, nonce: str, encrypt: str = "") -> bool:
    """校验签名是否匹配。"""
    expected = _sha1_signature(token, timestamp, nonce, encrypt)
    return expected == msg_signature


def _pkcs7_unpad(data: bytes) -> bytes:
    """PKCS#7 去填充。企微规范: 填充字节数 1-32。"""
    pad_len = data[-1]
    if pad_len < 1 or pad_len > 32:
        raise ValueError(f"Invalid PKCS#7 padding: {pad_len}")
    return data[:-pad_len]


def decrypt(encrypt: str) -> tuple[str, str]:
    """AES-CBC-256 解密企微消息。

    Returns:
        (xml_content, from_corp_id) — 解密后的 XML 字符串 和 企业ID
    """
    key = _get_aes_key()
    iv = key[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = base64.b64decode(encrypt)
    decrypted = cipher.decrypt(encrypted)
    decrypted = _pkcs7_unpad(decrypted)

    # 解密后内容: 16字节随机串 + 4字节msg_len(大端) + msg_content + corp_id
    msg_len = struct.unpack("!I", decrypted[16:20])[0]
    msg_content = decrypted[20:20 + msg_len].decode("utf-8")
    corp_id = decrypted[20 + msg_len:].decode("utf-8")
    return msg_content, corp_id


def parse_event_xml(xml_str: str) -> dict:
    """解析企微事件 XML，返回扁平字典。"""
    root = ET.fromstring(xml_str)
    return {child.tag: (child.text or "") for child in root}


def verify_url(msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
    """企微 URL 验证流程：校验签名 + 解密 echostr 返回明文。

    Args:
        msg_signature: 企微签名
        timestamp: 时间戳
        nonce: 随机串
        echostr: 加密的随机串

    Returns:
        解密后的明文 echostr（直接返回给企微）

    Raises:
        ValueError: 签名校验失败
    """
    token = get_settings().WECOM_CALLBACK_TOKEN
    # 注意: echostr 可能被 URL 编码（如 %2F, %3D），FastAPI 的 Query 会自动解码
    # 但如果是从 raw query string 拿的，需要手动 urllib.parse.unquote
    expected_sig = _sha1_signature(token, timestamp, nonce, echostr)
    if expected_sig != msg_signature:
        from loguru import logger
        logger.error(
            f"签名校验失败:\n"
            f"  期望: {expected_sig}\n"
            f"  实际: {msg_signature}\n"
            f"  token: {token}\n"
            f"  timestamp: {timestamp}\n"
            f"  nonce: {nonce}\n"
            f"  echostr: {echostr}"
        )
        raise ValueError(f"签名校验失败")
    plain, _ = decrypt(echostr)
    return plain

