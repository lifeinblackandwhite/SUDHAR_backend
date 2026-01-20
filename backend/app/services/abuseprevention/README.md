# Abuse Prevention Layer

The abuse prevention system validates uploaded images to ensure they are authentic and represent real, current issues. It uses **4 independent validators**, each checking a different aspect of image authenticity.

---

## Overall Flow

```
Image Upload → abuse_decision() → Run 4 Validators → Calculate Overall Score → APPROVE/REJECT
                                                              ↓
                                            Threshold: 30+ points = APPROVED
```

**Decision Logic:**
```python
MINIMUM_SCORE_THRESHOLD = 30

# Sum all validator scores
overall_score = ai_score + exif_score + gps_score + web_score

# Decision
if overall_score >= 30:
    APPROVED → Issue becomes UNDER_VERIFICATION
else:
    REJECTED → Issue becomes AUTO_REJECTED
```

---

## The 4 Validators

| Validator | What It Checks | Score Impact |
|-----------|---------------|--------------|
| **AIDetectionValidator** | Is the image AI-generated? | -80 to +50 |
| **EXIFValidator** | Was photo taken recently? | -30 to +30 |
| **GPSValidator** | Does GPS match user location? | -35 to +35 |
| **WebExistenceValidator** | Has image been seen before? | -40 to +15 |

---

## 1. AI Detection Validator

Detects if an image is AI-generated (Midjourney, DALL-E, Stable Diffusion, etc.)

### Checks Performed:
- **EXIF metadata authenticity**: AI images often lack or have fake EXIF data
- **Camera make/model**: Real photos have authentic camera info (Apple, Samsung, Canon, etc.)
- **Software signatures**: Scans for known AI tool names in metadata
- **Noise pattern analysis**: AI images have unusually uniform noise patterns

### Known AI Signatures Blocked:
```
midjourney, dall-e, stable diffusion, novelai, artbreeder, 
deepai, nightcafe, adobe firefly, bing image creator,
leonardo.ai, playground ai, dreamstudio, bluewillow
```

### Scoring:
| Condition | Score |
|-----------|-------|
| Valid EXIF with camera make/model | +25 to +35 |
| Known camera manufacturer | +10 |
| No EXIF data | -30 |
| AI software signature detected | -80 |
| Editing software detected | -10 |
| Unusually uniform noise pattern | -15 |

---

## 2. EXIF Timestamp Validator

Ensures the photo was taken recently (within 24 hours by default).

### Checks Performed:
- Presence of `DateTimeOriginal` or `DateTime` in EXIF
- Photo age calculation from EXIF timestamp

### Scoring:
| Age | Score |
|-----|-------|
| < 1 hour | +30 |
| 1-24 hours | +15 |
| > 24 hours | -25 |
| No timestamp | -20 |
| No EXIF data | -30 |

---

## 3. GPS Location Validator

Verifies the image GPS matches where the user is submitting from.

### How It Works:
1. Extracts GPS coordinates from image EXIF
2. Compares with user's submitted location using **Haversine formula**
3. Calculates distance between the two points

### Scoring:
| Distance | Score |
|----------|-------|
| < 100 meters | +35 ✅ |
| 100-500 meters | +20 ✅ |
| > 500 meters | -35 ❌ |
| No GPS data in EXIF | -20 to -25 |
| User location not provided | -20 |

---

## 4. Web Existence Validator (Duplicate Detection)

Checks if the image has been uploaded before or exists online.

### How It Works:
1. Calculates **perceptual hash (pHash)** of the image
2. Calculates **SHA256 hash** for exact matching
3. Compares against database of known image hashes
4. Uses **hamming distance** (≤5) for similar image detection

### Scoring:
| Result | Score |
|--------|-------|
| Not found (original) | +15 ✅ |
| Found exact SHA256 match | -40 ❌ |
| Found similar pHash (hamming ≤5) | -40 ❌ |

---

## Example Scenarios

| Scenario | AI | EXIF | GPS | Web | Total | Result |
|----------|-----|------|-----|-----|-------|--------|
| Fresh photo, right location | +40 | +30 | +35 | +15 | **120** | ✅ APPROVED |
| Old photo, no GPS | +30 | -25 | -20 | +15 | **0** | ❌ REJECTED |
| AI-generated image | -80 | -30 | -35 | +15 | **-130** | ❌ REJECTED |
| Re-uploaded duplicate | +40 | +15 | +20 | -40 | **35** | ✅ APPROVED |
| Photo with no EXIF | -30 | -30 | -25 | +15 | **-70** | ❌ REJECTED |

---

## Fail-Safe Behavior

If ANY error occurs during validation, the image is **automatically rejected**:

```python
except Exception as e:
    logger.error(f"Abuse prevention error: {e}")
    return False  # Reject on error
```

---

## File Structure

```
abuseprevention/
├── __init__.py
├── api.py              # FastAPI routes for testing
├── config.py           # Configuration settings
├── models.py           # Data models
├── service.py          # Main ImageValidationService
├── validators.py       # The 4 validators
├── test_validators.py  # Unit tests
└── README.md           # This file
```

---

## Usage

The abuse prevention is called during issue upload:

```python
from app.services.abuse_decision import abuse_decision

is_clean = await abuse_decision(
    issue, 
    image_bytes,
    latitude=latitude, 
    longitude=longitude
)

if is_clean:
    # Issue proceeds to UNDER_VERIFICATION
else:
    # Issue is AUTO_REJECTED
```

---

## Configuration

Key settings in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `max_age_hours` | 24 | Maximum photo age in hours |
| `max_distance_km` | 0.5 | Max GPS distance in km |
| `ai_threshold` | 0.7 | AI detection confidence threshold |
| `hamming_threshold` | 5 | Max hamming distance for similar images |

---

## Logging

All validation results are logged in detail:

```
==================================================
ABUSE PREVENTION VALIDATION RESULTS
==================================================
Issue ID: 123
Category: Water Leakage
User Lat/Lon: 12.9716, 77.5946
--------------------------------------------------
[AI_DETECTION]
  Passed: True
  Score: 45
  Reason: Image appears authentic
[EXIF]
  Passed: True
  Score: 30
  Reason: Image taken within the last hour
[GPS]
  Passed: True
  Score: 35
  Reason: GPS location matches exactly (45m away)
[WEB_EXISTENCE]
  Passed: True
  Score: 15
  Reason: Image not found in known image database
--------------------------------------------------
Overall Score: 125
FINAL DECISION: APPROVED
==================================================
```
