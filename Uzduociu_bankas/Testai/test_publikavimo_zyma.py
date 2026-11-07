import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Skriptai'))
import patikrinti_publikavimo_zyma as audit


class Backend:
    def __init__(self, local, registry):
        self.local, self.registry = local, registry
        self.calls = []

    def list(self):
        self.calls.append('list')
        return [{'Path': item['path'], 'ID': self.registry[task]['drive_id'],
                 'IsDir': False, 'Hashes': {'md5': item['md5']}}
                for task, item in self.local.items()]

    def api(self):
        self.calls.append('api')
        return self


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run_git('init', '-q')
        self.run_git('config', 'user.name', 'Test')
        self.run_git('config', 'user.email', 'test@example.invalid')
        bank = self.root / 'Uzduociu_bankas'
        self.registry = {}
        for n in range(1, 5):
            task = f'U{n:06d}'
            folder = bank / 'Uzdaviniai' / task
            folder.mkdir(parents=True)
            (folder / f'{task}.pdf').write_bytes(f'pdf {n}'.encode())
            fid = f'ID_{n}'
            self.registry[task] = {'drive_id': fid, 'url': f'https://drive.google.com/file/d/{fid}/view'}
        (bank / 'drive_links.json').write_text(json.dumps(self.registry))
        self.run_git('add', '.')
        self.run_git('commit', '-qm', 'base')
        self.base = self.run_git('rev-parse', 'HEAD')
        (bank / 'drive_publication_state.json').write_text(json.dumps({'last_published_commit': self.base}))
        self.commit('state')

    def run_git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.DEVNULL, text=True).strip()

    def commit(self, message):
        self.run_git('add', '.')
        self.run_git('commit', '-qm', message)
        self.target = self.run_git('rev-parse', 'HEAD')

    def test_all_verified_read_only_and_git_blob_not_dirty_worktree(self):
        (self.root / 'Uzduociu_bankas/Uzdaviniai/U000001/U000001.pdf').write_bytes(b'dirty')
        local, registry, checkpoint = audit.snapshot(self.root, self.target)
        self.assertEqual(checkpoint, self.base)
        backend = Backend(local, registry)
        with patch.object(audit.drive, 'process') as verify, contextlib.redirect_stdout(io.StringIO()):
            audit.verify(local, registry, backend)
        self.assertEqual(verify.call_count, 4)
        self.assertTrue(all(call.kwargs == {'apply': False, 'verify': True} for call in verify.call_args_list))
        self.assertEqual(backend.calls, ['list', 'api'])

    def test_missing_registry_or_pdf_rejected(self):
        path = self.root / 'Uzduociu_bankas/drive_links.json'
        del self.registry['U000004']
        path.write_text(json.dumps(self.registry))
        self.commit('missing registry')
        with self.assertRaises(audit.pub.PublicationError):
            audit.snapshot(self.root, self.target)

    def test_original_registry_id_must_be_preserved(self):
        path = self.root / 'Uzduociu_bankas/drive_links.json'
        self.registry['U000001'] = {'drive_id': 'OTHER', 'url': 'https://drive.google.com/file/d/OTHER/view'}
        path.write_text(json.dumps(self.registry))
        self.commit('changed id')
        with self.assertRaisesRegex(audit.pub.PublicationError, 'ankstesnis registro ID'):
            audit.snapshot(self.root, self.target)

    def test_deleted_pdf_rejected(self):
        self.run_git('rm', 'Uzduociu_bankas/Uzdaviniai/U000004/U000004.pdf')
        self.commit('deleted')
        with self.assertRaisesRegex(audit.pub.PublicationError, 'ištrintas PDF'):
            audit.snapshot(self.root, self.target)

    def test_target_must_equal_head_and_be_full_sha(self):
        for target in (self.base, self.target[:7]):
            with self.subTest(target=target), self.assertRaises(audit.pub.PublicationError):
                audit.snapshot(self.root, target)

    def test_remote_mismatch_and_access_failure(self):
        local, registry, _ = audit.snapshot(self.root, self.target)
        backend = Backend(local, registry)
        rows = backend.list()
        for key, value in [('ID', 'OTHER'), ('Hashes', {'md5': '0' * 32})]:
            modified = [dict(r) for r in rows]
            modified[0][key] = value
            with self.subTest(key=key), patch.object(backend, 'list', return_value=modified):
                with self.assertRaises(audit.pub.PublicationError):
                    audit.verify(local, registry, backend)
        with patch.object(audit.drive, 'process', side_effect=audit.drive.PatikrosKlaida('teisės')):
            with self.assertRaises(audit.drive.PatikrosKlaida):
                audit.verify(local, registry, backend)

    def test_extra_git_pdf_must_also_be_in_registry(self):
        path = self.root / 'Uzduociu_bankas/Uzdaviniai/U000005/U000005.pdf'
        path.parent.mkdir()
        path.write_bytes(b'extra')
        self.commit('extra')
        with self.assertRaises(audit.pub.PublicationError):
            audit.snapshot(self.root, self.target)


if __name__ == '__main__':
    unittest.main()
