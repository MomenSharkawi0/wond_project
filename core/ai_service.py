"""
Wound segmentation + risk scoring (OpenCV-based).

The naive approach of "thresholding red in HSV" fails on skin photographs
because pale skin itself passes a generous red threshold. This version:

1. Uses the LAB color space's `a` channel (red-green axis) which separates
   wound tissue from surrounding skin much more reliably than HSV
2. Picks an adaptive cutoff (mean + k*stdev, plus a high percentile) so the
   threshold scales with the actual color distribution of THIS image, not a
   hardcoded one
3. Additionally requires high HSV saturation, killing pale-skin false positives
4. Scores candidate blobs by `area * compactness²`, preferring round wound-like
   regions over long thin strips of skin
"""
import io
import os
import uuid
import numpy as np
import cv2
from PIL import Image


def _classify(risk_score: int) -> str:
    if risk_score >= 80:
        return "Critical"
    if risk_score >= 60:
        return "High"
    if risk_score >= 40:
        return "Medium"
    return "Stable"


def _segment(img_rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray | None]:
    """
    Returns (binary_wound_mask, contour). Mask is all zeros if no plausible
    wound was found.
    """
    h, w = img_rgb.shape[:2]
    total_pixels = h * w

    # LAB 'a' channel: 128 = neutral, >128 = redder, <128 = greener.
    lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
    a_channel = lab[..., 1]
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    s_channel = hsv[..., 1]

    # Adaptive red-threshold: keep only pixels that are statistical outliers
    # toward red AND have meaningful saturation. The stricter of (mean+1.5σ,
    # 92nd percentile) avoids both noisy and uniformly-red images.
    a_mean, a_std = float(a_channel.mean()), float(a_channel.std())
    a_pct = float(np.percentile(a_channel, 92))
    a_thresh = max(a_mean + 1.5 * a_std, a_pct, a_mean + 8.0)

    candidate = ((a_channel > a_thresh) & (s_channel > 50)).astype(np.uint8) * 255

    # Open then close — open kills thin strips, close fills wound interior gaps.
    k = np.ones((5, 5), np.uint8)
    candidate = cv2.morphologyEx(candidate, cv2.MORPH_OPEN, k, iterations=2)
    candidate = cv2.morphologyEx(candidate, cv2.MORPH_CLOSE, k, iterations=3)

    contours, _ = cv2.findContours(candidate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return np.zeros_like(candidate), None

    # Score each blob by area * compactness² so we prefer round wound-shaped
    # regions over long thin skin-coloured strips touching the image edge.
    best, best_score = None, 0.0
    min_area = total_pixels * 0.002  # ignore tiny specks (< 0.2% of image)
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area:
            continue
        perim = cv2.arcLength(c, closed=True)
        if perim <= 0:
            continue
        compactness = 4.0 * np.pi * area / (perim * perim)  # 1.0 = perfect circle
        score = area * (compactness ** 2)
        if score > best_score:
            best_score = score
            best = c

    if best is None:
        return np.zeros_like(candidate), None

    wound = np.zeros_like(candidate)
    cv2.drawContours(wound, [best], -1, 255, thickness=cv2.FILLED)
    return wound, best


def _render_overlay(img_rgb: np.ndarray, wound_mask: np.ndarray, contour) -> np.ndarray:
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    overlay = img_bgr.copy()
    if wound_mask.any():
        red_layer = np.zeros_like(img_bgr)
        red_layer[wound_mask > 0] = (0, 0, 255)  # BGR red
        overlay = cv2.addWeighted(overlay, 1.0, red_layer, 0.35, 0)
    if contour is not None:
        cv2.drawContours(overlay, [contour], -1, (0, 255, 255), thickness=2)
        M = cv2.moments(contour)
        if M["m00"]:
            cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
            cv2.circle(overlay, (cx, cy), 4, (0, 255, 255), -1)
    return overlay


def analyze_wound_image(image_bytes: bytes, upload_dir: str = "uploads", reference_width_cm: float = 15.0) -> dict:
    """
    reference_width_cm: real-world width that the full image frame represents.
        Used to convert pixel measurements to cm. 15 cm is a reasonable default
        for a smartphone photo of a limb at arm's length.

    Returns: { risk_score, wound_area_pixels, wound_area_cm2, wound_diameter_cm,
               coverage, severity, mask_path, reference_width_cm }
    """
    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return {
            "risk_score": 50, "wound_area_pixels": 0.0, "coverage": 0.0,
            "severity": "Medium", "mask_path": None,
        }

    img_rgb = np.array(pil_img)
    h, w = img_rgb.shape[:2]
    total_pixels = h * w

    wound_mask, contour = _segment(img_rgb)
    wound_pixels = int(wound_mask.sum() // 255) if wound_mask.any() else 0
    coverage = wound_pixels / total_pixels if total_pixels else 0.0

    if contour is not None and wound_pixels > 0:
        # Combine coverage with how much redder the wound is vs. surrounding skin
        lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
        a_channel = lab[..., 1].astype(np.float32)
        wound_a = float(a_channel[wound_mask > 0].mean())
        skin_a = float(a_channel[wound_mask == 0].mean()) if (wound_mask == 0).any() else wound_a
        redness_excess = max(0.0, (wound_a - skin_a) / 15.0)  # 0..~3

        # Calibration so visible wounds score reasonably:
        # ~1% coverage → ~25, ~5% → ~55, ~10% → ~75, ~20% → ~95
        risk_score = int(min(95, max(10, coverage * 600 + redness_excess * 22)))
    else:
        # No plausible wound detected
        risk_score = 8

    overlay = _render_overlay(img_rgb, wound_mask, contour)
    os.makedirs(upload_dir, exist_ok=True)
    mask_filename = f"mask_{uuid.uuid4().hex[:8]}.jpg"
    mask_path = os.path.join(upload_dir, mask_filename).replace("\\", "/")
    cv2.imwrite(mask_path, overlay)

    # Convert pixel measurements to cm using the user-supplied reference.
    cm_per_pixel = (reference_width_cm / w) if w > 0 else 0.0
    wound_area_cm2 = wound_pixels * (cm_per_pixel ** 2)
    wound_diameter_cm = 2.0 * (wound_area_cm2 / np.pi) ** 0.5 if wound_area_cm2 > 0 else 0.0

    return {
        "risk_score": risk_score,
        "wound_area_pixels": float(wound_pixels),
        "wound_area_cm2": round(wound_area_cm2, 2),
        "wound_diameter_cm": round(wound_diameter_cm, 2),
        "coverage": round(coverage, 4),
        "severity": _classify(risk_score),
        "mask_path": mask_path,
        "reference_width_cm": reference_width_cm,
    }
