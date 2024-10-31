from cerberus import Validator as _Validator
import pytest
import linkedin
import pprint

pp = pprint.PrettyPrinter(indent=4)
linkedin.BASE_CONFIG["cache"] = False


class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for adding non-standard keys to schema


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


def require_min_presence(items, key, min_perc=0.1):
    """check whether dataset contains items with some amount of non-null values for a given key"""
    count = sum(1 for item in items if item.get(key))
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )


profile_schema = {
    "profile": {
        "type": "dict",
        "schema": {
            "address": {
                "type": "dict",
                "schema": {
                    "addressLocality": {"type": "string"},
                    "addressCountry": {"type": "string"},
                }
            }
        }
    },
    "posts": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "name": {"type": "string"},
                "articleBody": {"type": "string"},
                "url": {"type": "string"},
            }
        }
    }
}

company_schema = {
    "overview": {
        "type": "dict",
        "schema": {
            "name": {"type": "string"},
            "url": {"type": "string"},
            "description": {"type": "string"},
            "numberOfEmployees": {"type": "integer"},
            "Industry": {"type": "string"},
            "Headquarters": {"type": "string"},
            "Founded": {"type": "string"},
            "Specialties": {"type": "string"},
        }
    }
}

job_search_schema = {
    "title": {"type": "string"},
    "company": {"type": "string"},
    "address": {"type": "string"},
    "timeAdded": {"type": "string"},
    "jobUrl": {"type": "string"},
    "companyUrl": {"type": "string"},
}

job_page_schema = {
    "datePosted": {"type": "string"},
    "employmentType": {"type": "string"},
    "industry": {"type": "string"},
    "title": {"type": "string"},
    "validThrough": {"type": "string"},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_profile_scraping():
    profile_data = await linkedin.scrape_profile(
        urls=[
            "https://www.linkedin.com/in/williamhgates"
        ]
    )
    validator = Validator(profile_schema, allow_unknown=True)
    for item in profile_data:
        validate_or_fail(item, validator)

    assert len(profile_data) == 1


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_company_scraping():
    company_data = await linkedin.scrape_company(
        urls=[
            "https://linkedin.com/company/microsoft",
            "https://linkedin.com/company/google",
            "https://linkedin.com/company/apple"
        ]
    )
    validator = Validator(company_schema, allow_unknown=True)
    for item in company_data:
        validate_or_fail(item, validator)

    for k in company_schema:
        require_min_presence(company_data, k, min_perc=company_schema[k].get("min_presence", 0.1))

    assert len(company_data) == 3


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_job_search_scraping():
    job_search_data = await linkedin.scrape_job_search(
        # it include other search parameters, refer to the search pages on browser for more details
        keyword="Python Developer",
        location="United States",
        max_pages=3
    )
    validator = Validator(job_search_schema, allow_unknown=True)
    for item in job_search_data:
        validate_or_fail(item, validator)

    for k in job_search_schema:
        require_min_presence(job_search_data, k, min_perc=job_search_schema[k].get("min_presence", 0.1))        

    assert len(job_search_data) > 20


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_job_page_scraping():
    job_search_data = await linkedin.scrape_job_search(
        # it include other search parameters, refer to the search pages on browser for more details
        keyword="Python Developer",
        location="United States",
        max_pages=1
    )
    job_urls = [i["jobUrl"] for i in job_search_data]

    job_data = await linkedin.scrape_jobs(
        urls=job_urls[:4]
    )
    validator = Validator(job_page_schema, allow_unknown=True)
    for item in job_data:
        validate_or_fail(item, validator)

    assert len(job_data) >= 1
