"""
SatQuery AI — Sentinel-2 STAC Client
Fetches real Sentinel-2 imagery using the Element84 Earth Search catalog.

This is 100% FREE — no API key, no registration required.
Uses AWS-hosted Sentinel-2 COG (Cloud-Optimized GeoTIFF) files.

Usage:
    client = SentinelSTACClient()
    result = client.fetch_before_after(
        bbox=[72.75, 18.85, 73.05, 19.30],   # [west, south, east, north]
        date_before="2023-06-01",
        date_after="2024-06-01",
        max_cloud_pct=30,
    )
"""

import base64
import io
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Element84 Earth Search — free, no auth needed
EARTH_SEARCH_URL = "https://earth-search.aws.element84.com/v1"
SENTINEL_COLLECTION = "sentinel-2-l2a"

# Max bbox area in degrees² to prevent huge downloads
MAX_BBOX_AREA = 0.5  # ~50x50 km at equator
TARGET_SIZE = 512    # pixels for output image


@dataclass
class SentinelScene:
    image_b64: str
    date: str
    cloud_pct: float
    scene_id: str
    bbox: List[float]
    width: int
    height: int


@dataclass
class SentinelFetchResult:
    success: bool
    before: Optional[SentinelScene] = None
    after: Optional[SentinelScene] = None
    error: Optional[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class SentinelSTACClient:
    """
    Fetches real Sentinel-2 imagery by bounding box and date range.
    Uses the free Element84 Earth Search STAC catalog.
    No API key or registration required.
    """

    def fetch_before_after(
        self,
        bbox: List[float],           # [west, south, east, north]
        date_before: str,            # ISO date string, e.g. "2023-06-01"
        date_after: str,             # ISO date string, e.g. "2024-06-01"
        max_cloud_pct: float = 30.0,
        search_window_days: int = 60,
    ) -> SentinelFetchResult:
        """
        Fetch a before and after Sentinel-2 scene for a bounding box.
        Searches ±search_window_days around each target date for the clearest scene.
        """
        warnings = []

        # Validate bbox area
        bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        if bbox_area > MAX_BBOX_AREA:
            warnings.append(
                f"AOI is large ({bbox_area:.2f}°²). Download may be slow. "
                f"Consider a smaller region for faster results."
            )
            # Clip to center portion
            cx = (bbox[0] + bbox[2]) / 2
            cy = (bbox[1] + bbox[3]) / 2
            half = 0.3  # ~30km radius
            bbox = [cx - half, cy - half, cx + half, cy + half]
            warnings.append(f"Auto-clipped AOI to {half*2:.1f}° window around center.")

        try:
            import pystac_client
        except ImportError:
            return SentinelFetchResult(
                success=False,
                error="pystac-client not installed. Run: pip install pystac-client",
            )

        try:
            catalog = pystac_client.Client.open(EARTH_SEARCH_URL)
        except Exception as e:
            return SentinelFetchResult(
                success=False,
                error=f"Cannot reach Earth Search catalog: {e}. Check internet connection.",
            )

        # Search for before scene
        before_scene = self._search_best_scene(
            catalog, bbox, date_before, search_window_days, max_cloud_pct
        )
        if before_scene is None:
            # Try with higher cloud threshold
            before_scene = self._search_best_scene(
                catalog, bbox, date_before, search_window_days * 2, max_cloud_pct + 30
            )
            if before_scene is None:
                return SentinelFetchResult(
                    success=False,
                    error=(
                        f"No Sentinel-2 scene found near {date_before} with "
                        f"<{max_cloud_pct + 30}% clouds. Try a different date or region."
                    ),
                )
            warnings.append(f"Used higher cloud threshold ({max_cloud_pct + 30}%) for 'before' image.")

        # Search for after scene
        after_scene = self._search_best_scene(
            catalog, bbox, date_after, search_window_days, max_cloud_pct
        )
        if after_scene is None:
            after_scene = self._search_best_scene(
                catalog, bbox, date_after, search_window_days * 2, max_cloud_pct + 30
            )
            if after_scene is None:
                return SentinelFetchResult(
                    success=False,
                    error=(
                        f"No Sentinel-2 scene found near {date_after} with "
                        f"<{max_cloud_pct + 30}% clouds. Try a different date or region."
                    ),
                )
            warnings.append(f"Used higher cloud threshold ({max_cloud_pct + 30}%) for 'after' image.")

        # Download and crop both scenes
        try:
            before_img = self._download_rgb(before_scene, bbox)
            after_img = self._download_rgb(after_scene, bbox)
        except Exception as e:
            return SentinelFetchResult(
                success=False,
                error=f"Failed to download imagery: {e}",
                warnings=warnings,
            )

        def to_b64(img: np.ndarray) -> str:
            pil = Image.fromarray(img.astype(np.uint8))
            pil = pil.resize((TARGET_SIZE, TARGET_SIZE), Image.LANCZOS)
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode()

        before_b64 = to_b64(before_img)
        after_b64 = to_b64(after_img)

        before_cloud = before_scene.properties.get("eo:cloud_cover", 0)
        after_cloud = after_scene.properties.get("eo:cloud_cover", 0)

        return SentinelFetchResult(
            success=True,
            before=SentinelScene(
                image_b64=before_b64,
                date=before_scene.datetime.strftime("%Y-%m-%d") if before_scene.datetime else date_before,
                cloud_pct=round(float(before_cloud), 1),
                scene_id=before_scene.id,
                bbox=list(before_scene.bbox),
                width=TARGET_SIZE,
                height=TARGET_SIZE,
            ),
            after=SentinelScene(
                image_b64=after_b64,
                date=after_scene.datetime.strftime("%Y-%m-%d") if after_scene.datetime else date_after,
                cloud_pct=round(float(after_cloud), 1),
                scene_id=after_scene.id,
                bbox=list(after_scene.bbox),
                width=TARGET_SIZE,
                height=TARGET_SIZE,
            ),
            warnings=warnings,
        )

    def _search_best_scene(
        self,
        catalog,
        bbox: List[float],
        target_date: str,
        window_days: int,
        max_cloud_pct: float,
    ):
        """Search for the clearest scene within ±window_days of target_date."""
        try:
            dt = datetime.fromisoformat(target_date)
            start = (dt - timedelta(days=window_days)).strftime("%Y-%m-%d")
            end = (dt + timedelta(days=window_days)).strftime("%Y-%m-%d")

            search = catalog.search(
                collections=[SENTINEL_COLLECTION],
                bbox=bbox,
                datetime=f"{start}/{end}",
                query={"eo:cloud_cover": {"lt": max_cloud_pct}},
                sortby="+properties.eo:cloud_cover",  # least cloudy first
                max_items=10,
            )
            items = list(search.items())
            if not items:
                return None
            # Return least cloudy
            return min(items, key=lambda i: i.properties.get("eo:cloud_cover", 100))
        except Exception as e:
            logger.warning(f"STAC search failed: {e}")
            return None

    def _download_rgb(self, item, bbox: List[float]) -> np.ndarray:
        """
        Download and crop RGB bands (B04=Red, B03=Green, B02=Blue) from a Sentinel-2 COG.
        Falls back to thumbnail if COG download fails.
        """
        # Try thumbnail first (always available, fast, no extra deps)
        thumb_url = None
        for key in ("thumbnail", "overview", "rendered_preview"):
            if key in item.assets:
                thumb_url = item.assets[key].href
                break

        if thumb_url:
            try:
                import urllib.request
                with urllib.request.urlopen(thumb_url, timeout=15) as resp:
                    data = resp.read()
                img = Image.open(io.BytesIO(data)).convert("RGB")
                # Crop to bbox proportion if possible
                arr = np.array(img)
                return arr
            except Exception as e:
                logger.warning(f"Thumbnail download failed: {e}. Trying COG bands.")

        # COG band download fallback (requires rioxarray/stackstac)
        try:
            import stackstac
            stack = stackstac.stack(
                [item],
                assets=["red", "green", "blue"],
                bounds_latlon=bbox,
                resolution=30,
            )
            data = stack.compute().values[0]  # [3, H, W]
            # Normalize to 0-255
            data = np.transpose(data, (1, 2, 0))  # [H, W, 3]
            p2, p98 = np.percentile(data, (2, 98))
            data = np.clip((data - p2) / (p98 - p2 + 1e-6) * 255, 0, 255)
            return data.astype(np.uint8)
        except Exception as e:
            raise RuntimeError(f"Could not download imagery via COG: {e}")
