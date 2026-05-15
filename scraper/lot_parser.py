from playwright.async_api import Page
import re


async def parse_lot(page: Page, lot_url: str) -> dict:
    """
    Atidaro Copart lot puslapį ir ištraukia visus duomenis.
    """

    print(f"[Parser] Parsing: {lot_url}")

    await page.goto(
        lot_url,
        wait_until="domcontentloaded"
    )

    lot_number = _extract_lot_number(lot_url)

    # React content loading
    await page.wait_for_timeout(7000)

    data = {
        "auction_url": lot_url,
        "lot_number": lot_number,
    }

    # =========================================================
    # PAVADINIMAS + METAI
    # =========================================================

    title = await _extract_title(page)

    if title:
        data["title"] = title

        year_match = re.search(r"\b(19|20)\d{2}\b", title)

        if year_match:
            data["year"] = int(year_match.group())

    # =========================================================
    # VIN
    # =========================================================

    vin = await _extract_vin(page)

    if vin:
        data["vin"] = vin.upper()

    # =========================================================
    # TECHNICAL INFO
    # =========================================================

    data["drivetrain"] = (
        await _get_field(page, "Drivetrain")
    )

    data["transmission"] = (
        await _get_field(page, "Transmission")
    )

    data["engine_type"] = (
        await _get_field(page, "Engine Type")
    )

    data["fuel"] = (
        await _get_field(page, "Fuel")
    )

    # =========================================================
    # ODOMETER
    # =========================================================

    odo_raw = (
        await _get_field(page, "Odometer")
        or
        await _get_field(page, "Mileage")
    )

    if odo_raw:

        nums = re.findall(r"[\d,]+", odo_raw)

        data["odometer"] = (
            int(nums[0].replace(",", ""))
            if nums else None
        )

        data["odometer_unit"] = (
            "mi"
            if "mi" in odo_raw.lower()
            else "km"
        )

    # =========================================================
    # DAMAGE
    # =========================================================

    data["damage_primary"] = (
        await _get_field(page, "Primary Damage")
    )

    data["damage_secondary"] = (
        await _get_field(page, "Secondary Damage")
    )

    data["loss_type"] = (
        await _get_field(page, "Loss Type")
    )

    # =========================================================
    # AUCTION INFO
    # =========================================================

    data["sale_date"] = (
        await _get_field(page, "Sale Date")
    )

    data["location"] = (
        await _get_field(page, "Location")
    )

    data["sale_status"] = (
        await _get_field(page, "Sale Status")
    )

    # =========================================================
    # EXTERIOR CONDITION
    # =========================================================

    data["exterior_condition"] = (
        await _extract_exterior_condition(page)
    )

    # =========================================================
    # IMAGE URLS
    # =========================================================

    data["image_urls"] = (
        await _extract_image_urls(page)
    )

    # Remove None values
    data = {
        k: v
        for k, v in data.items()
        if v is not None
    }

    return data


# =========================================================
# HELPERS
# =========================================================

def _extract_lot_number(url: str) -> str:

    match = re.search(r"/lot/(\d+)", url)

    return (
        match.group(1)
        if match
        else url.split("/")[-1]
    )


async def _extract_title(page: Page) -> str | None:

    """
    Ištraukia:
    2018 AUDI A4 PROGRESSIV
    """

    try:

        locator = page.locator("h1").first

        text = await locator.inner_text()

        text = text.strip()

        return text if text else None

    except Exception:

        return None


async def _extract_vin(page: Page) -> str | None:

    """
    Ištraukia VIN iš viršutinės juostos.
    """

    try:

        locator = page.locator("text=VIN:").first

        text = await locator.inner_text()

        match = re.search(
            r"VIN:\s*([A-Z0-9*]+)",
            text
        )

        if match:
            return match.group(1)

        return None

    except Exception:

        return None


async def _get_field(
    page: Page,
    label: str
) -> str | None:

    """
    Tikslesnis Copart field extraction.
    """

    try:

        text = await page.evaluate(f"""
        () => {{

            const elements = Array.from(
                document.querySelectorAll("*")
            );

            for (const el of elements) {{

                const txt = el.innerText?.trim();

                if (!txt)
                    continue;

                if (
                    txt.toLowerCase() ===
                    "{label.lower()}:"
                ) {{

                    const parent = el.parentElement;

                    if (!parent)
                        continue;

                    const children = Array.from(
                        parent.children
                    );

                    if (children.length >= 2) {{

                        const value =
                            children[1].innerText?.trim();

                        if (value)
                            return value;
                    }}
                }}
            }}

            return null;
        }}
        """)

        return text

    except Exception:

        return None


async def _extract_image_urls(
    page: Page
) -> list[str]:

    """
    Ištraukia TIK Copart galerijos
    nuotraukas teisinga tvarka.
    """

    try:

        urls = await page.evaluate("""
        () => {

            const results = [];

            const gallery = document.querySelectorAll(
                'img[src*="_thb.jpg"]'
            );

            gallery.forEach(img => {

                let src = img.src;

                if (!src)
                    return;

                src = src
                    .replace('_thb.jpg', '_ful.jpg')
                    .replace('_vthb.jpg', '_ful.jpg')
                    .replace('_116.jpg', '_ful.jpg');

                results.push(src);
            });

            return [...new Set(results)];
        }
        """)

        return urls

    except Exception as e:

        print(
            f"[Parser] "
            f"Image URL extraction error: {e}"
        )

        return []


async def _extract_exterior_condition(
    page: Page
) -> dict:

    """
    Exterior condition parser.
    """

    result = {
        "front_left": [],
        "front_right": [],
        "rear_left": [],
        "rear_right": [],
        "other": [],
    }

    try:

        sections = await page.query_selector_all(
            "div.detailed-description"
        )

        for section in sections:

            text = await section.inner_text()

            lines = [
                line.strip()
                for line in text.split("\n")
                if line.strip()
            ]

            if not lines:
                continue

            # Pirma eilutė = sekcijos pavadinimas
            raw_section = lines[0].lower().strip()

            section_name = (
                raw_section
                .replace(" ", "_")
            )

            # Tik valid sections
            if section_name not in result:
                continue

            # Likusios eilutės = damages
            damages = lines[1:]

            result[section_name] = damages

        return result

    except Exception as e:

        print(
            f"[Parser] "
            f"Exterior condition error: {e}"
        )

        return {}