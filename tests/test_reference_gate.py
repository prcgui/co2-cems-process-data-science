"""Reject stale or altered frozen-reference approvals before costly fitting."""
import json
import pytest
from iatan.data import digest
from iatan.experiments import gate


def frozen_tree(root):
    (root / 'configs').mkdir()
    (root / 'outputs/iatan_consolidado').mkdir(parents=True)
    model = root / 'model.json'; model.write_text('preserved model', encoding='utf-8')
    (root / 'configs/frozen_reference.json').write_text(json.dumps({'model_path': 'model.json', 'model_sha256': digest(model)}), encoding='utf-8')
    data = root / 'data.bin'; data.write_bytes(b'preserved observations')
    manifest = root / 'configs/iatan_inputs.json'
    manifest.write_text(json.dumps({'files': [{'path': 'data.bin', 'sha256': digest(data)}]}), encoding='utf-8')
    record = {'reference_verified': True, 'historical_retraining_verified': False,
              'reference_config_sha256': digest(root / 'configs/frozen_reference.json'),
              'inputs_manifest_sha256': digest(manifest)}
    (root / 'outputs/iatan_consolidado/reference_verified.json').write_text(json.dumps(record), encoding='utf-8')


def test_frozen_approval_does_not_claim_retraining(tmp_path):
    frozen_tree(tmp_path)
    assert 'historical_retraining_not_verified' in gate(tmp_path)


def test_model_change_invalidates_approval(tmp_path):
    frozen_tree(tmp_path)
    (tmp_path / 'model.json').write_text('different model', encoding='utf-8')
    with pytest.raises(RuntimeError, match='Modelo congelado alterado'): gate(tmp_path)


def test_data_change_invalidates_approval(tmp_path):
    frozen_tree(tmp_path)
    (tmp_path / 'data.bin').write_bytes(b'changed observations')
    with pytest.raises(ValueError, match='Insumo alterado'): gate(tmp_path)


def test_config_change_invalidates_approval(tmp_path):
    frozen_tree(tmp_path)
    p = tmp_path / 'configs/frozen_reference.json'
    p.write_text(p.read_text(encoding='utf-8') + ' ', encoding='utf-8')
    with pytest.raises(RuntimeError, match='desatualizada'): gate(tmp_path)
