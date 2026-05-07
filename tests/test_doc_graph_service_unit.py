from service.services import doc_graph_service


def test_document_key_includes_product_version_when_binding_is_version_scoped():
    binding = {"product_version_id": 23}

    key = doc_graph_service._document_key(binding)

    assert key == "doc_id: $doc_id, product_id: $product_id, product_version_id: $product_version_id"


def test_document_key_keeps_legacy_product_scope_without_version():
    binding = {"product_version_id": None}

    key = doc_graph_service._document_key(binding, doc_id_param="source_doc_id")

    assert key == "doc_id: $source_doc_id, product_id: $product_id"
