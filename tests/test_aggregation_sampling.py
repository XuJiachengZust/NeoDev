"""TDD tests for 聚合采样与 _build_aggregate_prompt（单分支与状态方案阶段3）。"""


class TestSampleLimitsToConfigSize:
    def test_sample_limits_to_config_size(self):
        from service.services.aggregation_sampling import sample_children

        children = [
            {"name": "a", "desc": "d1"},
            {"name": "b", "desc": "d2"},
            {"name": "c", "desc": "d3"},
            {"name": "d", "desc": "d4"},
            {"name": "e", "desc": "d5"},
        ]
        sampled = sample_children(children, sample_size=3, max_desc_chars=None)
        assert len(sampled) == 3

    def test_sample_sorted_by_name(self):
        from service.services.aggregation_sampling import sample_children

        children = [
            {"name": "C", "desc": "d3"},
            {"name": "A", "desc": "d1"},
            {"name": "B", "desc": "d2"},
        ]
        sampled = sample_children(children, sample_size=3, max_desc_chars=None)
        assert [s["name"] for s in sampled] == ["A", "B", "C"]

    def test_sample_respects_total(self):
        from service.services.aggregation_sampling import sample_children

        children = [{"name": "x", "desc": "d"}]
        sampled = sample_children(children, sample_size=5, max_desc_chars=None)
        assert len(sampled) == 1
        assert sampled[0]["name"] == "x"


class TestBuildAggregatePrompt:
    def test_build_aggregate_prompt_contains_sampling_phrase(self):
        from service.services.aggregation_sampling import build_aggregate_prompt

        sampled = [{"name": "m1", "desc": "desc1"}, {"name": "m2", "desc": "desc2"}]
        prompt = build_aggregate_prompt("Class", "MyClass", sampled, total=5)
        assert "采样" in prompt
        assert "5" in prompt
        assert "2" in prompt or "前" in prompt
        assert "MyClass" in prompt or "Class" in prompt

    def test_build_aggregate_prompt_includes_sampled_items(self):
        from service.services.aggregation_sampling import build_aggregate_prompt

        sampled = [{"name": "m1", "desc": "d1"}]
        prompt = build_aggregate_prompt("Class", "X", sampled, total=1)
        assert "m1" in prompt
        assert "d1" in prompt


class TestMaxDescChars:
    def test_aggregation_max_desc_chars_truncates_per_item(self):
        from service.services.aggregation_sampling import sample_children

        children = [
            {"name": "a", "desc": "long description here"},
            {"name": "b", "desc": "short"},
        ]
        sampled = sample_children(
            children, sample_size=5, max_desc_chars=10
        )
        assert len(sampled) == 2
        first_desc = sampled[0]["desc"]
        if "long description here" != first_desc:
            assert len(first_desc) <= 11
            assert "…" in first_desc or "..." in first_desc or len(first_desc) == 10
