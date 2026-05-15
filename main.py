import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.browser import create_browser, new_page
from scraper.lot_parser import parse_lot
from scraper.image_downloader import download_images
from db.mongo_client import CarsDB

def load_lot_urls() -> list[str]:

    with open("lot_urls2.txt", "r") as f:

        return [
            line.strip()
            for line in f.readlines()
            if line.strip()
        ]

async def scrape_lot(page, db: CarsDB, url: str):
    lot_number = url.rstrip("/").split("/")[-1]

    if db.lot_exists(lot_number):
        print(f"[Main] Lot {lot_number} jau DB, praleista")
        return

    # 1. Parse metadata + image URLs
    car_data = await parse_lot(page, url)
    if not car_data:
        print(f"[Main] Nepavyko parse'inti {url}")
        return

    # 2. Parsisiųsti nuotraukas
    image_urls = car_data.pop("image_urls", [])
    image_paths = await download_images(lot_number, image_urls)
    car_data["images"] = image_paths
    car_data["image_count"] = len(image_paths)

    # 3. Įrašyti į MongoDB
    db.insert_car(car_data)


async def main():
    db = CarsDB()
    browser, context = await create_browser()

    try:
        lot_urls = load_lot_urls()
        for url in lot_urls:
            page = await new_page(context)
            try:
                await scrape_lot(page, db, url)
            except Exception as e:
                print(f"[Main] Klaida {url}: {e}")
            finally:
                await page.close()

            await asyncio.sleep(5)
    finally:
        await browser.close()
        db.close()
        print("[Main] Baigta.")


if __name__ == "__main__":
    asyncio.run(main())