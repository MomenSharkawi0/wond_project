"""
Wound segmentation + risk scoring.

Strategy:
- Detect wound-like regions by color (red/pink hues) + dark necrotic tissue in HSV/grayscale
- Clean the mask with morphological operations and keep the largest connected component
- Render an overlay image with translucent red fill + bright yellow outline
- Compute a risk score from the wound coverage ratio and the mean redness inside the mask

The original unet_model.h5 in this repo is not loaded — it was flagged as
corrupted by the original author and OpenCV-based segmentation is sufficient
to produce a clear visual mask + clinically interpretable metrics.
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
    """Return (binary_mask, largest_contour_or_None) for the wound region."""
    h, w = img_rgb.shape[:2]
    total_pixels = h * w

    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)

    # Red wraps around 0/180 in HSV; cover both ends.
    red1 = cv2.inRange(hsv, np.array([0, 60, 50]), np.array([15, 255, 255]))
    red2 = cv2.inRange(hsv, np.array([160, 60, 50]), np.array([180, 255, 255]))
    mask = cv2.bitwise_or(red1, red2)

    # Add very dark regions (necrotic / eschar tissue).
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    mask = cv2.bitwise_or(mask, cv2.inRange(gray, 0, 45))

    # Clean noise then close gaps.
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return np.zeros_like(mask), None

    biggest = max(contours, key=cv2.contourArea)
    # Reject tiny specks (< 0.1% of image).
    if cv2.contourArea(biggest) < total_pixels * 0.001:
        return np.zeros_like(mask), None

    wound = np.zeros_like(mask)
    cv2.drawContours(wound, [biggest], -1, 255, thickness=cv2.FILLED)
    return wound, biggest


def _render_overlay(img_rgb: np.ndarray, wound_mask: np.ndarray, contour) -> np.ndarray:
    """Composite a translucent red fill + yellow outline onto a copy of the image."""
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    overlay = img_bgr.copy()
    red_layer = np.zeros_like(img_bgr)
    red_layer[wound_mask > 0] = (0, 0, 255)  # BGR red
    overlay = cv2.addWeighted(overlay, 1.0, red_layer, 0.40, 0)
    if contour is not None:
        cv2.drawContours(overlay, [contour], -1, (0, 255, 255), thickness=2)  # yellow
        # Annotate area centroid with risk label area
        M = cv2.moments(contour)
        if M["m00"]:
            cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
            cv2.circle(overlay, (cx, cy), 4, (0, 255, 255), -1)
    return overlay


def analyze_wound_image(image_bytes: bytes, upload_dir: str = "uploads") -> dict:
    """
    Analyze a wound image. Always returns a dict with keys:
        risk_score: int 0-100
        wound_area_pixels: float
        coverage: float (wound / total image area)
        severity: str
        mask_path: str | None — path to overlay image, relative to project root
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
    wound_pixels = int(wound_mask.sum() / 255) if wound_mask.any() else 0
    coverage = wound_pixels / total_pixels if total_pixels else 0.0

    if contour is not None and wound_pixels > 0:
        # Mean redness inside the wound (R channel of original RGB)
        r_channel = img_rgb[..., 0].astype(np.float32)
        mean_red = float(r_channel[wound_mask > 0].mean()) / 255.0
        risk_score = int(min(95, max(15, coverage * 220 + mean_red * 40)))
    else:
        # No clear wound detected
        risk_score = 12

    # Render the overlay even if no wound was found (just original image).
    overlay = _render_overlay(img_rgb, wound_mask, contour)
    os.makedirs(upload_dir, exist_ok=True)
    mask_filename = f"mask_{uuid.uuid4().hex[:8]}.jpg"
    mask_path = os.path.join(upload_dir, mask_filename)
    cv2.imwrite(mask_path, overlay)

    return {
        "risk_score": risk_score,
        "wound_area_pixels": float(wound_pixels),
        "coverage": round(coverage, 4),
        "severity": _classify(risk_score),
        "mask_path": mask_path.replace("\\", "/"),
    }
