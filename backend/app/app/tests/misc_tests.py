# import pytest
#
# from app.domain_service.play import ClientFactory
#
#
# class TestCaseCache:
#     @pytest.mark.skip("Skipped due to problems with Redis")
#     def test_connectionSetupAndValueStore(self):
#         rclient = ClientFactory().new_client()
#         rclient.set("test_key", "test_value")
#         v = rclient.get("test_key")
#         assert v == b"test_value"
