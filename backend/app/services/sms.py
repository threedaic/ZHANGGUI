"""
腾讯云短信服务
- 存酒通知: 短信含瓶身码和取酒链接
- 取酒通知: 短信通知客人取酒完成
"""
from loguru import logger
from app.config import get_settings

settings = get_settings()


async def _get_client():
    """创建腾讯云 SMS 客户端"""
    from tencentcloud.common import credential
    from tencentcloud.sms.v20210111 import sms_client

    if not settings.SMS_SECRET_ID or not settings.SMS_SDK_APP_ID:
        logger.warning("腾讯云短信未配置，跳过发送")
        return None

    cred = credential.Credential(settings.SMS_SECRET_ID, settings.SMS_SECRET_KEY)
    return sms_client.SmsClient(cred, "ap-guangzhou")


async def send_stored_sms(phone: str, customer_name: str, wine_name: str,
                           bottle_label: str, remaining_ml: int) -> bool:
    """存酒通知短信"""
    client = await _get_client()
    if not client:
        return True  # 未配置时静默跳过，不影响存酒

    if not settings.SMS_TEMPLATE_ID_STORED:
        logger.warning("存酒短信模板 ID 未配置")
        return True

    capacity_map = {750: "满瓶", 562: "3/4瓶", 375: "1/2瓶", 187: "1/4瓶"}
    capacity = capacity_map.get(remaining_ml, str(remaining_ml))

    try:
        from tencentcloud.sms.v20210111 import models
        req = models.SendSmsRequest()
        req.SmsSdkAppId = settings.SMS_SDK_APP_ID
        req.SignName = settings.SMS_SIGN_NAME
        req.TemplateId = settings.SMS_TEMPLATE_ID_STORED
        req.TemplateParamSet = [customer_name, wine_name, capacity, bottle_label]
        req.PhoneNumberSet = [f"+86{phone}"]

        resp = client.SendSms(req)
        logger.info(f"存酒短信已发送: {phone} {wine_name} status={resp.SendStatusSet[0].Code}")
        return True
    except Exception as e:
        logger.error(f"存酒短信发送失败 phone={phone}: {e}")
        return False


async def send_retrieved_sms(phone: str, customer_name: str, wine_name: str,
                              retrieve_ml: int, bottle_label: str) -> bool:
    """取酒通知短信"""
    client = await _get_client()
    if not client:
        return True

    if not settings.SMS_TEMPLATE_ID_RETRIEVED:
        logger.warning("取酒短信模板 ID 未配置")
        return True

    try:
        from tencentcloud.sms.v20210111 import models
        req = models.SendSmsRequest()
        req.SmsSdkAppId = settings.SMS_SDK_APP_ID
        req.SignName = settings.SMS_SIGN_NAME
        req.TemplateId = settings.SMS_TEMPLATE_ID_RETRIEVED
        req.TemplateParamSet = [customer_name, wine_name, str(retrieve_ml), bottle_label]
        req.PhoneNumberSet = [f"+86{phone}"]

        resp = client.SendSms(req)
        logger.info(f"取酒短信已发送: {phone} {wine_name} status={resp.SendStatusSet[0].Code}")
        return True
    except Exception as e:
        logger.error(f"取酒短信发送失败 phone={phone}: {e}")
        return False
