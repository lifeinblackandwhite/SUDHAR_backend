from app.services.abuseprevention.service import ImageValidationService
from app.services.abuseprevention.config import Config
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

# Minimum score threshold for approval (0-100 scale)
# Lower = more lenient, Higher = stricter
MINIMUM_SCORE_THRESHOLD = 20  # Lenient threshold for MVP

async def abuse_decision(issue, image_bytes: bytes | None = None, *, latitude: float, longitude: float) -> bool:
    if not image_bytes:
        logger.warning("[ABUSE] No image provided → reject")
        return False

    try:
        service = ImageValidationService(
            db_connection=None,
            config=Config()
        )

        result = service.validate_image(
            image_data=image_bytes,
            user_latitude=latitude,
            user_longitude=longitude,
            store_hash=True
        )

        # 🔍 DETAILED DEBUG LOGGING
        logger.info("=" * 50)
        logger.info("ABUSE PREVENTION VALIDATION RESULTS")
        logger.info("=" * 50)
        logger.info(f"Issue ID: {issue.id}")
        logger.info(f"Category: {issue.category}")
        logger.info(f"User Lat/Lon: {latitude}, {longitude}")
        logger.info("-" * 50)
        
        # Log each check's result
        for check_name, check_result in result.checks.items():
            passed = check_result.get('passed', 'N/A')
            score = check_result.get('score', 'N/A')
            reason = check_result.get('reason', 'N/A')
            logger.info(f"[{check_name.upper()}]")
            logger.info(f"  Passed: {passed}")
            logger.info(f"  Score: {score}")
            logger.info(f"  Reason: {reason}")
        
        logger.info("-" * 50)
        logger.info(f"Overall Score: {result.overall_score}")
        logger.info(f"All Checks Passed: {result.is_valid}")
        logger.info(f"Reasons: {result.reasons}")
        logger.info("=" * 50)

        # MVP Decision: Use score-based validation instead of requiring all checks to pass
        # This allows images with missing EXIF/GPS to still be accepted if they score high enough
        is_approved = result.overall_score >= MINIMUM_SCORE_THRESHOLD
        
        if is_approved != result.is_valid:
            logger.info(f"[MVP MODE] Overriding strict validation. Score {result.overall_score} >= threshold {MINIMUM_SCORE_THRESHOLD}")
        
        logger.info(f"FINAL DECISION: {'APPROVED' if is_approved else 'REJECTED'}")
        
        return is_approved

    except Exception as e:
        # --------------------------------------------------
        # ❗ Fail-safe: any error → reject
        # --------------------------------------------------
        logger.error(f"Abuse prevention error: {e}", exc_info=True)
        return False
