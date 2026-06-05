import json
from pathlib import Path

from scraper.io import append_rows_to_csv
from scraper.ipo.sources import (
    fetch_all_ipo_source_records,
    parse_announcement_result_page,
    parse_ipo_result_page,
    parse_nepselink_ipo_opening_page,
    parse_sharehub_ipo_page,
    parse_upcoming_ipo_page,
)


def _build_sharehub_html(offerings: list[dict]) -> str:
    """Recreate the Next.js RSC stream that sharehubnepal embeds the data in."""
    payload = (
        '7:["$","$L22",null,{"initialData":' + json.dumps(offerings) + ',"isLoading":false}]\n'
    )
    script = "<script>self.__next_f.push([1," + json.dumps(payload) + "])</script>"
    return f"<!doctype html><html><body><div id='app'></div>{script}</body></html>"


def test_parse_upcoming_ipo_page() -> None:
    html = """
    <div class="announcement-list">
      <div class="media">
        <small class="text-muted">2026-03-21</small>
        <div class="media-body">
          <a href="/NewsDetail.aspx?newsID=88888">Upper Tamakoshi Hydropower Limited is going to issue its 1,000,000 units IPO from 2026-03-22 to 2026-03-26</a>
        </div>
      </div>
    </div>
    """

    rows = parse_upcoming_ipo_page(html, "https://merolagani.com")
    assert len(rows) == 1
    assert rows[0]["source"] == "merolagani_upcoming"
    assert rows[0]["url"] == "https://merolagani.com/NewsDetail.aspx?newsID=88888"


def test_parse_ipo_result_page() -> None:
    html = """
    <div class="featured-news-list">
      <a href="/NewsDetail.aspx?newsID=77777"><h4>IPO allotment result published for Guardian Micro Life Insurance Limited</h4></a>
      <span class="text-org">2026-03-23</span>
    </div>
    """

    rows = parse_ipo_result_page(html, "https://merolagani.com")
    assert len(rows) == 1
    assert "allotment" in rows[0]["title"].lower()


def test_parse_ipo_result_page_ignores_generic_result_title() -> None:
    html = """
    <div class="featured-news-list">
      <a href="/IpoResult.aspx"><h4>IPO Results</h4></a>
      <span class="text-org">2026-03-23</span>
    </div>
    """

    rows = parse_ipo_result_page(html, "https://merolagani.com/IpoResult.aspx")
    assert rows == []


def test_parse_announcement_result_page() -> None:
    html = """
    <div class="announcement-list">
      <div class="media">
        <small class="text-muted">Apr 04, 2026</small>
        <div class="media-body">
          <a href="/AnnouncementDetail.aspx?id=64978">Kalanga Hydro Limited has distributed its 3,50,000.00 units of IPO shares to the Nepalese citizens working abroad</a>
        </div>
      </div>
    </div>
    """

    rows = parse_announcement_result_page(html, "https://merolagani.com/AnnouncementList.aspx")
    assert len(rows) == 1
    assert rows[0]["source"] == "merolagani_announcements"
    assert rows[0]["url"] == "https://merolagani.com/AnnouncementDetail.aspx?id=64978"


def test_parse_nepselink_ipo_opening_page() -> None:
    html = """
    <table>
      <tr>
        <th>IPO Type</th><th>Company Name</th><th>Units</th><th>Price per Unit</th>
        <th>Minimum Apply</th><th>Open Date</th><th>Close Date</th><th>Status</th>
      </tr>
      <tr>
        <td>IPO-General</td><td>Kalinchowk Hydropower Limited</td><td>684750</td><td>100</td>
        <td>10</td><td>2082-12-22</td><td>2082-12-25</td><td>Coming Soon</td>
      </tr>
      <tr>
        <td>IPO-GENERAL</td><td>Shikhar Power Development Limited</td><td>1842600</td><td>100</td>
        <td>10</td><td>2082-11-17</td><td>2082-11-22</td><td>Closed</td>
      </tr>
    </table>
    """

    rows = parse_nepselink_ipo_opening_page(html, "https://nepselink.com/ipo-opening")

    assert len(rows) == 2
    assert rows[0]["source"] == "nepselink_ipo_opening"
    assert rows[0]["company"] == "Kalinchowk Hydropower Limited"
    assert rows[0]["issue_open_date"] == "2082-12-22"
    assert rows[0]["issue_status"] == "upcoming"
    assert rows[0]["announcement_date"] == "2082-12-22"
    assert rows[1]["issue_status"] == "closed"
    assert rows[1]["announcement_date"] == "2082-11-22"


def test_parse_sharehub_ipo_page() -> None:
    html = _build_sharehub_html(
        [
            {
                "id": 3832,
                "slug": "3832-ipo-general-public-mount-everest-power-development-limited",
                "symbol": "MEPDL",
                "name": "Mount Everest Power Development Limited",
                "units": 1427600,
                "price": 100,
                "openingDate": "2026-06-17T00:00:00",
                "closingDate": "2026-06-22T00:00:00",
                "type": "Ipo",
                "for": "GeneralPublic",
                "status": "ComingSoon",
            },
            {
                "id": 3837,
                "slug": "3837-bond-nabil-debenture",
                "symbol": "NABIL8",
                "name": "8% Nabil Perpetual Non cumulative Preference Share",
                "units": 5000000,
                "price": 100,
                "openingDate": None,
                "closingDate": None,
                "type": "BondOrDebenture",
                "for": "GeneralPublic",
                "status": "Closed",
            },
            {"id": 1, "slug": "x", "name": "", "type": "Ipo"},  # skipped: no name
        ]
    )

    rows = parse_sharehub_ipo_page(
        html, "https://sharehubnepal.com/investment/upcoming-public-offerings"
    )

    assert len(rows) == 2

    ipo = rows[0]
    assert ipo["source"] == "sharehub_ipo"
    assert ipo["symbol"] == "MEPDL"
    assert ipo["company"] == "Mount Everest Power Development Limited"
    assert ipo["issue_type"] == "ipo"
    assert ipo["issue_open_date"] == "2026-06-17"
    assert ipo["issue_close_date"] == "2026-06-22"
    assert ipo["total_quantity"] == 1427600.0
    assert ipo["price_per_unit"] == 100.0
    assert ipo["issue_status"] == "upcoming"
    assert ipo["url"].endswith("/3832-ipo-general-public-mount-everest-power-development-limited")

    debenture = rows[1]
    assert debenture["issue_type"] == "debenture"
    assert debenture["issue_status"] == "closed"


def test_parse_sharehub_ipo_page_without_payload_returns_empty() -> None:
    assert parse_sharehub_ipo_page("<html><body>no data</body></html>", "https://x") == []


def test_parse_sharehub_ipo_page_ignores_non_array_initial_data() -> None:
    payload = '7:["$","$L22",null,{"initialData":null,"sidebar":[{"name":"Not An Offering"}]}]\n'
    script = "<script>self.__next_f.push([1," + json.dumps(payload) + "])</script>"

    assert parse_sharehub_ipo_page(f"<html><body>{script}</body></html>", "https://x") == []


def test_append_rows_to_csv(tmp_path: Path) -> None:
    target = tmp_path / "sample.csv"
    fieldnames = ["a", "b"]
    count = append_rows_to_csv(target, [{"a": 1, "b": 2}], fieldnames)

    assert count == 1
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "a,b" in content
    assert "1,2" in content


def test_append_rows_to_csv_dedupes_by_keys(tmp_path: Path) -> None:
    target = tmp_path / "sample_dedup.csv"
    fieldnames = ["scraped_at_utc", "symbol", "value"]

    first_count = append_rows_to_csv(
        target,
        [
            {"scraped_at_utc": "2026-03-29T07:30:00+00:00", "symbol": "ACLBSL", "value": 1},
            {"scraped_at_utc": "2026-03-29T07:30:00+00:00", "symbol": "NABIL", "value": 2},
        ],
        fieldnames,
        unique_key_fields=["scraped_at_utc", "symbol"],
    )
    second_count = append_rows_to_csv(
        target,
        [
            {"scraped_at_utc": "2026-03-29T07:30:00+00:00", "symbol": "ACLBSL", "value": 99},
            {"scraped_at_utc": "2026-03-29T08:00:00+00:00", "symbol": "ACLBSL", "value": 3},
        ],
        fieldnames,
        unique_key_fields=["scraped_at_utc", "symbol"],
    )

    assert first_count == 2
    assert second_count == 1

    lines = target.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 4
    assert "2026-03-29T07:30:00+00:00,ACLBSL,1" in lines
    assert "2026-03-29T08:00:00+00:00,ACLBSL,3" in lines


def test_fetch_all_ipo_source_records_tolerates_source_processing_error(monkeypatch) -> None:
    from scraper.ipo import sources

    def broken_upcoming() -> list[dict]:
        raise ValueError("unexpected parser failure")

    monkeypatch.setattr(sources, "fetch_sharehub_ipo_records", lambda: [])
    monkeypatch.setattr(sources, "fetch_upcoming_ipo_records", broken_upcoming)
    monkeypatch.setattr(sources, "fetch_nepselink_ipo_opening_records", lambda: [])
    monkeypatch.setattr(sources, "fetch_ipo_result_records", lambda: [])
    monkeypatch.setattr(sources, "fetch_nepse_ipo_disclosure_records", lambda client=None: [])

    bundle = fetch_all_ipo_source_records()

    assert bundle["sharehub_sources"] == []
    assert bundle["upcoming_sources"] == []
    assert bundle["merolagani_upcoming_sources"] == []
    assert bundle["result_sources"] == []
    assert bundle["nepse_disclosure_sources"] == []
    assert bundle["nepselink_sources"] == []
