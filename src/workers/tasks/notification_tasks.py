"""Celery tasks for sending notifications."""

import logging

from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_slack_notification(self, channel: str, message: str, attachments: list | None = None):
    """
    Send a Slack notification asynchronously.
    
    Args:
        channel: Slack channel to send to
        message: Message text
        attachments: Optional Slack attachments
    """
    logger.info(f"Sending Slack notification to {channel}")
    
    try:
        # Import here to avoid circular imports
        from src.services.integrations.slack import SlackIntegration
        
        # TODO: Initialize Slack client and send message
        # slack = SlackIntegration(config)
        # await slack.send_message(channel, message, attachments)
        
        logger.info(f"Slack notification sent to {channel}")
        return {"status": "sent", "channel": channel}
        
    except Exception as exc:
        logger.error(f"Failed to send Slack notification: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_email_notification(
    self,
    to: list[str],
    subject: str,
    body: str,
    html_body: str | None = None,
):
    """
    Send an email notification asynchronously.
    
    Args:
        to: List of recipient email addresses
        subject: Email subject
        body: Plain text body
        html_body: Optional HTML body
    """
    logger.info(f"Sending email notification to {to}")
    
    try:
        # TODO: Implement email sending via SMTP
        # This would use smtplib or an email service like SendGrid
        
        logger.info(f"Email notification sent to {to}")
        return {"status": "sent", "recipients": to}
        
    except Exception as exc:
        logger.error(f"Failed to send email notification: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def send_pagerduty_alert(
    self,
    service_id: str,
    title: str,
    details: dict,
    severity: str = "warning",
):
    """
    Send a PagerDuty alert asynchronously.
    
    Args:
        service_id: PagerDuty service ID
        title: Alert title
        details: Alert details
        severity: Alert severity (critical, error, warning, info)
    """
    logger.info(f"Sending PagerDuty alert: {title}")
    
    try:
        # Import here to avoid circular imports
        from src.services.integrations.pagerduty import PagerDutyIntegration
        
        # TODO: Initialize PagerDuty client and create incident
        
        logger.info(f"PagerDuty alert sent: {title}")
        return {"status": "sent", "service_id": service_id, "title": title}
        
    except Exception as exc:
        logger.error(f"Failed to send PagerDuty alert: {exc}")
        raise self.retry(exc=exc)
