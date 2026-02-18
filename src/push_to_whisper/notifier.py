import logging
from typing import Optional

import apprise

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self, settings):
        self.settings = settings

    def notify(self, title: str, body: str, urls: Optional[list[str]] = None):
        """Send notification to specified URLs (or configuration defaults)"""
        # If urls argument is None (no explicit override), use configuration defaults
        target_urls = (
            urls if urls is not None else self.settings.defaults.apprise.get("urls", [])
        )

        if not target_urls:
            logger.debug("No notification URLs provided. Skipping notification.")
            return

        try:
            logger.info(f"Sending notification to {len(target_urls)} targets: {title}")
            apobj = apprise.Apprise()
            for url in target_urls:
                apobj.add(url)
            apobj.notify(title=title, body=body)
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
