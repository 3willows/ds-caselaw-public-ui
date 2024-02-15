from unittest.mock import patch

from django.test import RequestFactory, TestCase

from judgments.resolvers.document_resolver_engine import DocumentResolverEngine


class TestDocumentResolverEngine(TestCase):
    @patch("judgments.resolvers.document_resolver_engine.get_best_pdf")
    @patch("judgments.resolvers.document_resolver_engine.get_generated_pdf")
    @patch("judgments.resolvers.document_resolver_engine.detail_xml")
    @patch("judgments.resolvers.document_resolver_engine.detail")
    def test_resolver_engine_with_fileformats(
        self,
        mock_detail,
        mock_detail_xml,
        mock_get_generated_pdf,
        mock_get_best_pdf,
    ):
        document_uri = "ewhc/comm/2024/253"
        test_params = [
            ("data.pdf", mock_get_best_pdf),
            ("generated.pdf", mock_get_generated_pdf),
            ("data.xml", mock_detail_xml),
            ("data.html", mock_detail),
        ]
        for file_format, view in test_params:
            with self.subTest(filename=file_format, view=view):
                path = document_uri + "/" + file_format
                request = RequestFactory().get(path)
                resolver_engine = DocumentResolverEngine()
                resolver_engine.setup(request)
                resolver_engine.dispatch(request, document_uri, file_format=file_format)

                view.assert_called_with(request, document_uri)
