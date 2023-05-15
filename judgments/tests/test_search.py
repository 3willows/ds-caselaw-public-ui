from datetime import datetime
from logging import WARNING
from typing import Any
from unittest.mock import patch

import pytest
from dateutil import parser as dateparser
from django.test import TestCase
from lxml import etree

from judgments.models import SearchResult, SearchResults


def fake_search_results():
    with open("fixtures/search_results.xml", "r") as f:
        return SearchResults.create_from_string(f.read())


def fake_search_result(
    uri="ewhc/ch/2022/1.xml",
    neutral_citation="[2022] EWHC 1 (Ch)",
    name="A SearchResult name!",
    matches=[],
    court="A court!",
    date="2022-01-01T00:01:00",
    author="",
    last_modified="2022-01-01T00:01:00.123",
    content_hash="A hash!",
    transformation_date="2022-01-01T00:02:00",
):
    return SearchResult(
        uri=uri,
        neutral_citation=neutral_citation,
        name=name,
        matches=matches,
        court=court,
        date=date,
        author=author,
        last_modified=last_modified,
        content_hash=content_hash,
        transformation_date=transformation_date,
    )


class TestBrowseResults(TestCase):
    @patch("judgments.views.browse.perform_advanced_search")
    @patch("judgments.models.SearchResult.create_from_node")
    def test_browse_results(self, fake_result, fake_advanced_search):
        fake_advanced_search.return_value = fake_search_results()
        fake_result.return_value = fake_search_result()
        response = self.client.get("/ewhc/ch/2022")
        fake_advanced_search.assert_called_with(
            court="ewhc/ch",
            date_from="2022-01-01",
            date_to="2022-12-31",
            order="-date",
            page=1,
            per_page=10,
        )
        self.assertContains(
            response,
            "A SearchResult name!",
        )


class TestSearchResults(TestCase):
    @patch("judgments.views.results.perform_advanced_search")
    @patch("judgments.models.SearchResult.create_from_node")
    def test_judgment_results(self, fake_result, fake_advanced_search):
        fake_advanced_search.return_value = fake_search_results()
        fake_result.return_value = fake_search_result()
        response = self.client.get("/judgments/results?query=waltham+forest")
        fake_advanced_search.assert_called_with(
            query="waltham forest", page="1", order="-relevance", per_page="10"
        )
        self.assertContains(
            response,
            '<span class="results-search-component__removable-options-value-text">waltham forest</span>',
        )

    @patch("judgments.views.results.perform_advanced_search")
    @patch("judgments.models.SearchResult.create_from_node")
    @patch("judgments.views.results.preprocess_query")
    def test_jugdment_results_query_preproccesed(
        self, fake_preprocess_query, fake_result, fake_advanced_search
    ):
        fake_advanced_search.return_value = fake_search_results()
        fake_result.return_value = fake_search_result()
        fake_preprocess_query.return_value = "normalised query"
        self.client.get("/judgments/results?query=waltham+forest")

        fake_preprocess_query.assert_called()

    @patch("judgments.views.advanced_search.perform_advanced_search")
    @patch("judgments.models.SearchResult.create_from_node")
    def test_judgment_advanced_search(self, fake_result, fake_advanced_search):
        fake_advanced_search.return_value = fake_search_results()
        fake_result.return_value = fake_search_result()
        response = self.client.get("/judgments/advanced_search?query=waltham+forest")
        self.assertContains(
            response,
            '<span class="results-search-component__removable-options-value-text">waltham forest</span>',
        )
        fake_advanced_search.assert_called_with(
            query="waltham forest",
            court=[],
            judge=None,
            party=None,
            neutral_citation=None,
            specific_keyword=None,
            page="1",
            order="relevance",
            date_from=None,
            date_to=None,
            per_page="10",
        )

    @patch("judgments.views.advanced_search.perform_advanced_search")
    @patch("judgments.models.SearchResult.create_from_node")
    @patch("judgments.views.advanced_search.preprocess_query")
    def test_judgment_advanced_search_query_preprocessed(
        self, fake_preprocess_query, fake_result, fake_advanced_search
    ):
        fake_advanced_search.return_value = fake_search_results()
        fake_result.return_value = fake_search_result()
        fake_preprocess_query.return_value = "normalised query"
        self.client.get("/judgments/advanced_search?query=waltham+forest")
        fake_preprocess_query.assert_called()


class TestSearchResult(TestCase):
    @patch("judgments.models.api_client")
    def test_create_from_node(self, fake_client):
        client_attrs = {
            "get_property.return_value": "something fake",
            "get_last_modified.return_value": "01-01-2022",
        }
        fake_client.configure_mock(**client_attrs)
        search_result_str = """
        <search:result xmlns:search="http://marklogic.com/appservices/search" index="1" uri="/ukut/lc/2022/241.xml">
            <search:snippet/>
            <search:extracted kind="element">
                <FRBRdate xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0" date="2022-09-09" name="decision"/>
                <FRBRdate xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0" date="2022-10-10" name="transform"/>
                <FRBRname xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
                          value="London Borough of Waltham Forest v Nasim Hussain"/>
                <uk:court xmlns:uk="https://caselaw.nationalarchives.gov.uk/akn">UKUT-LC</uk:court>
                <uk:cite xmlns:uk="https://caselaw.nationalarchives.gov.uk/akn">[2022] UKUT 241 (LC)</uk:cite>
                <uk:hash xmlns:uk="https://caselaw.nationalarchives.gov.uk/akn">
                    56c551fef5be37cb1658c895c1d15c913e76b712ba3ccc88d3b6b75ea69d3e8a
                </uk:hash>
                <neutralCitation xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
                    [2022] UKUT 241 (LC)
                </neutralCitation>
            </search:extracted>
        </search:result>
        """
        search_result_xml = etree.fromstring(search_result_str)
        search_result = SearchResult.create_from_node(search_result_xml)
        self.assertEqual(
            "London Borough of Waltham Forest v Nasim Hussain", search_result.name
        )
        self.assertEqual("ukut/lc/2022/241", search_result.uri)
        self.assertEqual("[2022] UKUT 241 (LC)", search_result.neutral_citation)
        self.assertEqual("UKUT-LC", search_result.court.code)
        self.assertEqual(dateparser.parse("2022-09-09"), search_result.date)
        self.assertEqual("2022-10-10", search_result.transformation_date)

    @patch("judgments.models.api_client")
    def test_create_from_node_with_missing_elements(self, fake_client):
        client_attrs = {
            "get_property.return_value": "something fake",
            "get_last_modified.return_value": "01-01-2022",
        }
        fake_client.configure_mock(**client_attrs)
        search_result_str = """
        <search:result xmlns:search="http://marklogic.com/appservices/search" index="1" uri="/ukut/lc/2022/241.xml">
            <search:snippet/>
            <search:extracted kind="element">
                <FRBRdate xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0" date="2022-09-09" name="decision"/>
                <FRBRname xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
                          value="London Borough of Waltham Forest v Nasim Hussain"/>
                <uk:cite xmlns:uk="https://caselaw.nationalarchives.gov.uk/akn"></uk:cite>
                <uk:court xmlns:uk="https://caselaw.nationalarchives.gov.uk/akn"></uk:court>
                <uk:hash xmlns:uk="https://caselaw.nationalarchives.gov.uk/akn"></uk:hash>
                <uk:court xmlns:uk="https://caselaw.nationalarchives.gov.uk/akn"></uk:court>
            </search:extracted>
        </search:result>
        """
        search_result_xml = etree.fromstring(search_result_str)
        search_result = SearchResult.create_from_node(search_result_xml)
        self.assertEqual(
            "London Borough of Waltham Forest v Nasim Hussain", search_result.name
        )
        self.assertEqual("ukut/lc/2022/241", search_result.uri)
        self.assertEqual(None, search_result.neutral_citation)
        self.assertEqual(None, search_result.court)
        self.assertEqual(None, search_result.content_hash)


class TestSearchResultInit:
    @pytest.mark.parametrize(
        "date_string, expected",
        [
            ["", None],
            ["2023-05-09", datetime(2023, 5, 9, 0, 0)],
            ["2023-04-05T06:54:00", datetime(2023, 4, 5, 6, 54)],
            ["ffffff", None],
        ],
    )
    def test_searchresult_date_parsing(self, date_string: str, expected: Any):
        search_result = fake_search_result(date=date_string)

        assert search_result.date == expected

    def test_unparseable_non_empty_string_logs_warning(self, caplog):
        caplog.set_level(WARNING)

        fake_search_result(date="ffffff")

        assert "Unable to parse document date" in caplog.text

    def test_unparseable_empty_string_doesnt_log_warning(self, caplog):
        caplog.set_level(WARNING)

        fake_search_result(date="")

        assert "Unable to parse document date" not in caplog.text
