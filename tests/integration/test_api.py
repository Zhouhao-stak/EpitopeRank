"""Tests for FastAPI endpoints."""

import logging

import pytest
from fastapi.testclient import TestClient
from epitoperank.api.app import create_app


@pytest.fixture
def client():
    """Create test client for API endpoints."""
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """The API health endpoint returns a ready status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

    def test_health_returns_version(self, client):
        """Test health endpoint includes version info."""
        response = client.get("/api/health")
        data = response.json()
        assert data["version"]


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_endpoint(self, client):
        """The root endpoint serves the browser application."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "EpitopeRank" in response.text


class TestFavicon:
    """Test favicon endpoint."""

    def test_favicon_endpoint(self, client):
        """Test /favicon.ico returns SVG."""
        response = client.get("/favicon.ico")
        assert response.status_code == 200
        assert "svg" in response.headers.get("content-type", "").lower()


class TestProjectEndpoints:
    """Test project management endpoints."""

    def test_list_projects_empty(self, client):
        """Test listing projects when none exist."""
        response = client.get("/api/projects")
        # Should not crash even if no projects exist
        assert response.status_code in [200, 404]

    def test_project_status_invalid(self, client):
        """Test project status with invalid ID."""
        response = client.get("/api/status/invalid-id")
        assert response.status_code == 404

    def test_neoantigen_reuses_project_and_original_cds(self, client, monkeypatch, tmp_path):
        import epitoperank.api.app as api_module
        import epitoperank.neoantigen as neo
        source = tmp_path / 'standardized'; source.mkdir()
        cds = tmp_path / 'splice_orfs.tsv'
        cds.write_text('event_id\treference_cds\taltered_cds\tjunction_nt\nSE:1\tATG\tATG\t3\n', encoding='utf-8')
        monkeypatch.setenv('EPITOPERANK_INGEST_ALLOW_EXTERNAL', '1')
        monkeypatch.setattr(api_module, 'project_status', lambda *_: {'project': {'source_dir': str(source)}})
        monkeypatch.setattr(neo, 'run', lambda directory, table, output, **kwargs: {'input_dir': str(directory), 'cds_table': str(table)})
        response = client.post('/api/neoantigen/run', json={'project_id': 'p1'})
        assert response.status_code == 200
        assert response.json()['cds_table'] == str(cds)
        cds.unlink()
        response = client.post('/api/neoantigen/run', json={'project_id': 'p1'})
        assert response.status_code == 422
        assert '编码序列表' in response.json()['detail']

    def test_neoantigen_workflow_advances_one_stage_and_rejects_stale_request(self, client, monkeypatch, tmp_path):
        import epitoperank.api.app as api_module
        import epitoperank.data.loader as loader
        from epitoperank.data.loader import Dataset
        from epitoperank.splicing.schema import parse_event_row
        ds = Dataset('test', tmp_path, 'standard', [parse_event_row({'event_id': 'a'})], [])
        monkeypatch.setenv('EPITOPERANK_INGEST_ALLOW_EXTERNAL', '1')
        monkeypatch.setattr(api_module, 'project_status', lambda *_: {'project': {'source_dir': str(tmp_path)}})
        monkeypatch.setattr(loader, 'load_dataset', lambda _: ds)
        started = client.post('/api/neoantigen/workflow/start', json={'project_id': 'p', 'evidence': {}})
        assert started.status_code == 200
        workflow_id = started.json()['workflow_id']
        assert client.get('/api/neoantigen/workflow/' + workflow_id).json()['next_stage'] == 1
        params = {'confirm': True, 'input_is_quantified_events': True, 'event_set': 'unknown'}
        request = {'workflow_id': workflow_id, 'expected_stage': 1, 'parameters': params}
        assert client.post('/api/neoantigen/workflow/advance', json=request).json()['next_stage'] == 2
        assert client.post('/api/neoantigen/workflow/advance', json=request).status_code == 409

    def test_mopepgen_uses_project_files_and_keeps_results(self, tmp_path, client, monkeypatch):
        import json
        from pathlib import Path
        import epitoperank.api.app as api_module
        import epitoperank.mopepgen_docker as runner
        monkeypatch.setenv('EPITOPERANK_INGEST_ALLOW_EXTERNAL', '1')
        monkeypatch.setattr(api_module, 'project_status', lambda *_: {'project': {'source_dir': str(tmp_path)}})
        for name in ('se.txt', 'genome.fa', 'reference.gtf', 'proteome.fa'):
            (tmp_path / name).write_text('example')
        def fake_run(args):
            output = Path(args[args.index('--output') + 1]); output.mkdir(parents=True)
            (output / 'manifest.json').write_text(json.dumps({'status':'complete'}))
            return 0
        monkeypatch.setattr(runner, 'execute', fake_run)
        payload = {'project_id':'p', 'se':'se.txt', 'genome':'genome.fa', 'gtf':'reference.gtf',
                   'proteome':'proteome.fa', 'reference_source':'GENCODE', 'reference_version':'test'}
        response = client.post('/api/neoantigen/mopepgen', json=payload)
        assert response.status_code == 200
        path = response.json()['output_dir']
        assert client.get('/api/neoantigen/mopepgen/file', params={'output_dir':path,'name':'manifest.json'}).status_code == 200
        (tmp_path / 'SE.MATS.JC.txt').write_text('rMATS test')
        payload['se'] = ''
        assert client.post('/api/neoantigen/mopepgen', json=payload).status_code == 200
        payload['genome'] = '../outside.fa'
        assert client.post('/api/neoantigen/mopepgen', json=payload).status_code == 422

    def test_neo_readiness_checks_project_and_cds_header(self, tmp_path, client, monkeypatch):
        import epitoperank.api.app as api_module
        import epitoperank.data.loader as loader
        from epitoperank.data.loader import Dataset
        from epitoperank.splicing.schema import parse_event_row
        ds = Dataset('test', tmp_path, 'standard', [parse_event_row({'event_id': 'a'})], [])
        monkeypatch.setenv('EPITOPERANK_INGEST_ALLOW_EXTERNAL', '1')
        monkeypatch.setattr(api_module, 'project_status', lambda *_: {'project': {'source_dir': str(tmp_path), 'name': 'P'}})
        monkeypatch.setattr(loader, 'load_dataset', lambda _: ds)
        url = '/api/neoantigen/readiness/p'
        assert client.get(url).json()['cds_status'] == 'missing'
        # An incomplete table is reported as a near miss instead of a hard failure.
        path = tmp_path / 'splice_orfs.tsv'; path.write_text('event_id\treference_cds\nSE:1\tATG\n', encoding='utf-8')
        body = client.get(url).json()
        assert body['cds_status'] == 'missing'
        assert body['cds_partial'][0]['name'] == 'splice_orfs.tsv'
        assert 'altered_cds' in body['cds_partial'][0]['reason']
        # A header without data rows is not usable yet.
        path.write_text('event_id\treference_cds\taltered_cds\tjunction_nt\n', encoding='utf-8')
        assert client.get(url).json()['cds_status'] == 'missing'
        path.write_text('event_id\treference_cds\taltered_cds\tjunction_nt\nSE:1\tATG\tATG\t3\n', encoding='utf-8')
        body = client.get(url).json()
        assert body['cds_status'] == 'available'
        assert body['cds_selected'] == 'splice_orfs.tsv'
        # A second, differently named table is a choice, not an error.
        (tmp_path / 'coding_pairs.csv').write_text(
            'event_id,reference_cds,altered_cds,junction_nt\nSE:1,ATG,ATG,3\n', encoding='utf-8')
        body = client.get(url).json()
        assert body['cds_status'] == 'available'
        assert body['cds_files'] == ['splice_orfs.tsv', 'coding_pairs.csv']
        assert body['cds_selected'] == 'splice_orfs.tsv'
        # Customer-style file names are discovered by header alone.
        (tmp_path / '客户CDS对照.tsv').write_text(
            '事件ID\t参考序列\t变异序列\t连接点\nSE:1\tATG\tATG\t3\n', encoding='utf-8')
        body = client.get(url).json()
        assert '客户CDS对照.tsv' in body['cds_files']


class TestAnalyzeEndpoint:
    """Test analysis endpoint."""

    def test_analyze_missing_input(self, client):
        """Test analyze without input file."""
        response = client.post("/api/analyze", json={})
        assert response.status_code == 400

    def test_analyze_with_invalid_query(self, client):
        """Test analyze with empty query."""
        response = client.post(
            "/api/analyze",
            json={"query": ""},
        )
        assert response.status_code == 400


class TestReportEndpoint:
    """Test report generation endpoints."""

    def test_report_not_found(self, client):
        """Test report for non-existent project."""
        response = client.get("/api/report/invalid-id")
        assert response.status_code == 404


class TestAPIErrorHandling:
    """Test API error handling."""

    def test_404_handler(self, client):
        """Test 404 handler for unknown routes."""
        response = client.get("/nonexistent-route")
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Test method not allowed."""
        # POST to GET-only endpoint
        response = client.post("/api/health")
        assert response.status_code == 405

    def test_debug_endpoint_is_not_exposed(self, client, caplog):
        """开发期用过的调试接口不得对外暴露，也不得把凭证写进日志。

        该端点曾用于排查上传问题（回显表单字段并吞掉异常），属于开发遗留：
        它无鉴权、无载荷处理，会把内部细节暴露给任何能访问端口的人。现予删除，
        并用 404 断言锁死，避免以后被重新加回来。
        """
        caplog.set_level(logging.INFO)
        response = client.post(
            "/api/upload-debug",
            headers={"Authorization": "Bearer do-not-log-this"},
            data={},
        )
        assert response.status_code == 404
        assert "do-not-log-this" not in caplog.text


class TestAPIHeaders:
    """Test API response headers."""

    def test_content_type_json(self, client):
        """Test JSON endpoints return correct content type."""
        response = client.get("/api/health")
        assert "application/json" in response.headers.get("content-type", "")

    def test_openapi_documentation(self, client):
        """The generated OpenAPI document exposes the public API contract."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert response.json()["info"]["title"] == "EpitopeRank API"

    def test_security_and_request_headers(self, client):
        """Responses expose a correlation id and baseline browser hardening."""
        response = client.get("/api/health")
        assert response.headers["x-request-id"]
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"


class TestAPIKeyAuthentication:
    """API key protection is opt-in for deployments exposed beyond localhost."""

    def test_configured_key_protects_api_routes(self, monkeypatch):
        monkeypatch.setenv("EPITOPERANK_API_KEY", "test-secret")
        protected_client = TestClient(create_app())

        assert protected_client.get("/api/projects").status_code == 401
        assert protected_client.get(
            "/api/projects", headers={"X-API-Key": "wrong"}
        ).status_code == 401
        assert protected_client.get(
            "/api/projects", headers={"X-API-Key": "test-secret"}
        ).status_code == 200

    def test_health_remains_available_for_probes(self, monkeypatch):
        monkeypatch.setenv("EPITOPERANK_API_KEY", "test-secret")
        protected_client = TestClient(create_app())

        assert protected_client.get("/api/health").status_code == 200


class TestAPIRateLimit:
    """Rate limiting is opt-in for deployments exposed beyond localhost."""

    def test_configured_rate_limit_returns_retry_after(self, monkeypatch):
        monkeypatch.setenv("EPITOPERANK_RATE_LIMIT", "2")
        limited_client = TestClient(create_app())

        assert limited_client.get("/api/projects").status_code == 200
        assert limited_client.get("/api/projects").status_code == 200
        response = limited_client.get("/api/projects")

        assert response.status_code == 429
        assert int(response.headers["retry-after"]) >= 1
        assert limited_client.get("/api/health").status_code == 200


class TestHistoryEndpoints:
    """A stored project must stay browsable after the run is over."""

    @pytest.fixture
    def stored_project(self, tmp_path, monkeypatch):
        """Create an isolated runtime root with one persisted project."""
        monkeypatch.setenv("EPITOPERANK_RUNTIME_ROOT", str(tmp_path))
        from epitoperank.config import load_prepared_settings
        from epitoperank.memory.project_memory import ProjectMemory
        from epitoperank.splicing.schema import StandardEvent

        settings, _warnings = load_prepared_settings()
        memory = ProjectMemory(settings.paths.memory_db)
        memory.create_project("SPN-HISTORY", "history-demo", "differential splicing", source_format="rMATS")
        events = [
            StandardEvent(
                event_id=f"SE:{index}",
                gene_id=f"ENSG{index:05d}",
                gene_symbol=gene,
                event_type="SE",
                chromosome="chr1",
                strand="+",
                genomic_coordinates=f"chr1:{1000 + index}-{1100 + index}",
                coordinate_system="1-based-inclusive",
                source_tool="rMATS",
                mean_psi_group1=0.8,
                mean_psi_group2=0.3,
                delta_psi=delta,
                p_value=0.001,
                fdr=0.01 if index < 2 else 0.9,
            )
            for index, (gene, delta) in enumerate([("VEGFA", -0.5), ("TP53", 0.42), ("MYC", 0.05)])
        ]
        memory.save_events("SPN-HISTORY", events, {"SE:0", "SE:1"})
        return TestClient(create_app())

    def test_project_list_carries_counters(self, stored_project):
        response = stored_project.get("/api/projects")
        assert response.status_code == 200
        project = next(p for p in response.json()["projects"] if p["project_id"] == "SPN-HISTORY")
        assert project["event_count"] == 3
        assert project["significant_count"] == 2

    def test_event_browser_pages_and_filters(self, stored_project):
        page = stored_project.get("/api/projects/SPN-HISTORY/events?page=1&size=2")
        assert page.status_code == 200
        payload = page.json()
        assert payload["total"] == 3
        assert payload["pages"] == 2
        assert len(payload["events"]) == 2

        significant = stored_project.get("/api/projects/SPN-HISTORY/events?significant_only=true")
        assert significant.json()["total"] == 2

        searched = stored_project.get("/api/projects/SPN-HISTORY/events?q=vegfa")
        assert [row["gene_symbol"] for row in searched.json()["events"]] == ["VEGFA"]

    def test_unknown_project_events_returns_404(self, stored_project):
        assert stored_project.get("/api/projects/NOPE/events").status_code == 404

    def test_delete_project_clears_database(self, stored_project):
        assert stored_project.delete("/api/projects/SPN-HISTORY").status_code == 200
        assert stored_project.get("/api/status/SPN-HISTORY").status_code == 404

    def test_storage_endpoint_reports_runtime_root(self, stored_project, tmp_path):
        payload = stored_project.get("/api/storage").json()
        assert payload["runtime_root"] == str(tmp_path.resolve())
        assert payload["databases"]["epitoperank.sqlite3"]["exists"] is True
