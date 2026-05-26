import scrapy
from twocaptcha import TwoCaptcha


class HyndaiRecallsSpider(scrapy.Spider):
    name = "hyndai_recalls"

    allowed_domains = ["recall.hyundaicanada.com"]

    start_urls = [
        "https://recall.hyundaicanada.com/"
    ]



    # VIN NUMBER
    vin_number = "5NMSG13E39H320413"

    def parse(self, response):

        # -------------------------------------------------
        # GET CAPTCHA SITEKEY
        # -------------------------------------------------
        site_key = response.xpath(
            '//div[@class="g-recaptcha"]/@data-sitekey'
        ).get()

        # -------------------------------------------------
        # GET VERIFICATION TOKEN
        # -------------------------------------------------
        verification_token = response.xpath(
            '//input[@name="__RequestVerificationToken"]/@value'
        ).get()

        self.logger.info(f"SITE KEY: {site_key}")
        self.logger.info(f"VERIFICATION TOKEN: {verification_token}")

        if not site_key:
            self.logger.error("Captcha sitekey not found")
            return

        if not verification_token:
            self.logger.error("Verification token not found")
            return

        # -------------------------------------------------
        # SOLVE CAPTCHA
        # -------------------------------------------------
        solver = TwoCaptcha(
            '502fc1e128765c5641b4f520a141bcf5'
        )

        try:
            result = solver.recaptcha(
                sitekey=site_key,
                url=response.url
            )

            captcha_token = result.get("code")

            self.logger.info(
                f"CAPTCHA SOLVED: {captcha_token}"
            )

        except Exception as e:
            self.logger.error(
                f"Captcha solve failed: {e}"
            )
            return

        # -------------------------------------------------
        # PAYLOAD
        # -------------------------------------------------
        payload = {
            "__RequestVerificationToken": verification_token,
            "VINNumber": self.vin_number,
            "g-recaptcha-response": captcha_token
        }

        self.logger.info(f"PAYLOAD: {payload}")

        # -------------------------------------------------
        # HEADERS
        # -------------------------------------------------
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://recall.hyundaicanada.com",
            "Referer": "https://recall.hyundaicanada.com/",
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/avif,"
                "image/webp,*/*;q=0.8"
            )
        }

        # -------------------------------------------------
        # SEND POST REQUEST
        # -------------------------------------------------
        yield scrapy.FormRequest(
            url="https://recall.hyundaicanada.com/Home/Results",
            formdata=payload,
            headers=headers,
            callback=self.parse_results,
            dont_filter=True
        )

    def parse_results(self, response):

        self.logger.info(
            f"STATUS CODE: {response.status}"
        )

        # SAVE RESPONSE
        with open(
            "results.html",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(response.text)

        # -------------------------------------------------
        # EXTRACT WARRANTY START DATE
        # -------------------------------------------------
        warranty_start_date = response.xpath(
            '//label[@data-i18n="warranty-start-date"]/parent::p/text()'
        ).get()

        if warranty_start_date:
            warranty_start_date = (
                warranty_start_date.strip()
            )

        self.logger.info(
            f"WARRANTY START DATE: "
            f"{warranty_start_date}"
        )

        # -------------------------------------------------
        # EXTRACT RECALL TABLE DATA
        # -------------------------------------------------
        recalls = []

        rows = response.xpath('//table//tr')

        for row in rows[1:]:

            recalls.append({
                "campaign_number": row.xpath(
                    './td[1]//text()'
                ).get(default='').strip(),

                "description": row.xpath(
                    './td[2]//text()'
                ).get(default='').strip(),

                "status": row.xpath(
                    './td[3]//text()'
                ).get(default='').strip(),
            })

        # -------------------------------------------------
        # FINAL OUTPUT
        # -------------------------------------------------
        yield {
            "vin_number": self.vin_number,
            "warranty_start_date": warranty_start_date,
            "recalls": recalls,
            "url": response.url
        }