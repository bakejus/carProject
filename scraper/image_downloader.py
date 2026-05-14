import asyncio
import aiohttp
import os
import re

from config import IMAGES_DIR, MAX_CONCURRENT_DOWNLOADS

from PIL import Image
from io import BytesIO


IMAGE_ORDER = {
    0: "front_left",
    1: "rear_left",
    2: "rear_right",
    3: "front_right",
    4: "front",
    5: "rear",
}


async def download_images(
    lot_number: str,
    image_urls: list[str]
) -> dict[str, str]:

    """
    Parsisiunčia pagrindines Copart nuotraukas.
    """

    if not image_urls:
        return {}

    lot_dir = os.path.join(IMAGES_DIR, lot_number)
    os.makedirs(lot_dir, exist_ok=True)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

    saved_paths = {}

    async with aiohttp.ClientSession(
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36"
            ),
            "Referer": "https://www.copart.com/",
        }
    ) as session:

        tasks = [
            _download_one(
                session,
                semaphore,
                url,
                index,
                lot_dir,
            )
            for index, url in enumerate(image_urls)
        ]

        results = await asyncio.gather(
            *tasks,
            return_exceptions=True
        )

    for result in results:

        if isinstance(result, tuple):

            angle, path = result

            saved_paths[angle] = path

    print(
        f"[Downloader] Lot {lot_number}: "
        f"saved {len(saved_paths)} images"
    )

    return saved_paths


async def _download_one(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    url: str,
    index: int,
    lot_dir: str,
) -> tuple[str, str] | None:

    async with semaphore:

        try:

            # Imame tik pagrindinius 6 kampus
            angle = IMAGE_ORDER.get(index)

            if angle is None:
                return None

            ext = _get_extension(url)

            filename = f"{angle}{ext}"

            filepath = os.path.join(
                lot_dir,
                filename
            )

            if os.path.exists(filepath):
                return angle, filepath

            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:

                if resp.status == 404:
                    return None

                if resp.status != 200:
                    print(
                        f"[Downloader] ✗ {url} "
                        f"→ HTTP {resp.status}"
                    )
                    return None

                content = await resp.read()

                # Patikrinam ar tai normali foto
                image = Image.open(BytesIO(content))

                width, height = image.size

                # Atmetam thumbnailus
                if width < 700 or height < 500:
                    print(
                        f"[Downloader] "
                        f"Skipped thumbnail: {url}"
                    )
                    return None

                with open(filepath, "wb") as f:
                    f.write(content)

                print(f"[Downloader] ✓ {filename}")

                return angle, filepath

        except Exception as e:

            print(
                f"[Downloader] "
                f"Error downloading {url}: {e}"
            )

            return None


def _get_extension(url: str) -> str:

    match = re.search(
        r"\.(jpg|jpeg|png|webp)(\?|$)",
        url.lower()
    )

    return f".{match.group(1)}" if match else ".jpg"