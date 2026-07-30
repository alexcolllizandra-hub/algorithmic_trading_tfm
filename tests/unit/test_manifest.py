from perp_lab.data.manifest import read_manifest, write_manifest
from perp_lab.utils.hashing import sha256_file


def test_write_manifest_creates_files_and_hash(tmp_path, klines_5m):
    data_path = tmp_path / "validated" / "BTCUSDT" / "5m.parquet"
    manifests_dir = tmp_path / "manifests"
    manifest = write_manifest(
        klines_5m,
        data_path=data_path,
        manifests_dir=manifests_dir,
        dataset_id="binance_um_BTCUSDT_klines_5m",
        source="unit-test",
        exchange="binance",
        market_type="um",
        symbol="BTCUSDT",
        stream="klines",
        timeframe="5m",
        repo_root=tmp_path,
    )
    assert data_path.exists()
    manifest_file = manifests_dir / "binance_um_BTCUSDT_klines_5m.json"
    assert manifest_file.exists()
    assert manifest.row_count == klines_5m.height
    assert manifest.data_sha256 == sha256_file(data_path)


def test_manifest_hash_is_stable(tmp_path, klines_5m):
    kwargs = {
        "manifests_dir": tmp_path / "m",
        "dataset_id": "ds",
        "source": "t",
        "exchange": "binance",
        "market_type": "um",
        "symbol": "BTCUSDT",
        "stream": "klines",
        "timeframe": "5m",
        "repo_root": tmp_path,
    }
    m1 = write_manifest(klines_5m, data_path=tmp_path / "a.parquet", **kwargs)
    m2 = write_manifest(klines_5m, data_path=tmp_path / "b.parquet", **kwargs)
    assert m1.data_sha256 == m2.data_sha256


def test_manifest_roundtrip(tmp_path, klines_5m):
    manifests_dir = tmp_path / "manifests"
    write_manifest(
        klines_5m,
        data_path=tmp_path / "x.parquet",
        manifests_dir=manifests_dir,
        dataset_id="ds",
        source="t",
        exchange="binance",
        market_type="um",
        symbol="BTCUSDT",
        stream="klines",
        timeframe="5m",
        repo_root=tmp_path,
    )
    loaded = read_manifest(manifests_dir / "ds.json")
    assert loaded.symbol == "BTCUSDT"
    assert loaded.timeframe == "5m"
