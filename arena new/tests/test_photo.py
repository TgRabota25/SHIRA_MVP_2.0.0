"""Проверки режима «Фото»: группировка, имена, реестр операций.
Работают без OCR и без GUI — классификация подменяется заглушкой.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))

from photo import (  # noqa: E402
    OP_COPY, OP_MOVE, Group, PhotoRegistry, classify_photos, execute_plan,
    natural_key, sanitize_stem, split_groups, unique_destination,
)

P = lambda *parts: Path(*parts)


class GroupingTests(unittest.TestCase):
    def test_split_groups_basic(self):
        # A-разделитель + 2 обычных + B-разделитель + 2 обычных → две группы по 3
        paths = [P('x/01_A.png'), P('x/02_f1.jpg'), P('x/03_f2.jpg'), P('x/04_B.png'), P('x/05_f3.jpg'), P('x/06_f4.jpg')]
        cls = {P('x/01_A.png'): 'A', P('x/04_B.png'): 'B'}
        groups, park = split_groups(paths, cls)
        self.assertEqual([g.label for g in groups], ['Товар A', 'Товар B'])
        self.assertEqual([p.name for p in groups[0].all_items], ['01_A.png', '02_f1.jpg', '03_f2.jpg'])
        self.assertEqual([p.name for p in groups[1].all_items], ['04_B.png', '05_f3.jpg', '06_f4.jpg'])
        self.assertEqual(park, [])

    def test_split_groups_photo_at_end(self):
        # 2 обычных + A + 2 обычных + B (в конце): до первого — парковка, в конце — продолжение последней группы
        paths = [P('x/01_f1.jpg'), P('x/02_f2.jpg'), P('x/03_A.png'), P('x/04_f3.jpg'), P('x/05_f4.jpg'), P('x/06_B.png')]
        cls = {P('x/03_A.png'): 'A', P('x/06_B.png'): 'B'}
        groups, park = split_groups(paths, cls)
        self.assertEqual([g.label for g in groups], ['Товар A', 'Товар B'])
        self.assertEqual([p.name for p in groups[0].all_items], ['03_A.png', '04_f3.jpg', '05_f4.jpg'])
        self.assertEqual([p.name for p in groups[1].all_items], ['06_B.png'])
        self.assertEqual([p.name for p, _ in park], ['01_f1.jpg', '02_f2.jpg'])

    def test_split_groups_no_separators_all_park(self):
        paths = [P('x/1.jpg'), P('x/2.jpg')]
        groups, park = split_groups(paths, {})
        self.assertEqual(groups, [])
        self.assertEqual(len(park), 2)

    def test_split_groups_ambiguous_park(self):
        paths = [P('x/01_A.png'), P('x/02_f1.jpg'), P('x/03_AB.png'), P('x/04_f2.jpg')]
        cls = {P('x/01_A.png'): 'A', P('x/03_AB.png'): 'ambiguous', P('x/04_B.png'): 'B'}
        groups, park = split_groups(paths, cls)
        self.assertEqual(len(groups), 1)
        self.assertEqual([p.name for p, _ in park], ['03_AB.png', '04_f2.jpg'])

    def test_split_groups_adjacent_separators(self):
        paths = [P('x/01_A.png'), P('x/02_A2.png'), P('x/03_f1.jpg')]
        cls = {P('x/01_A.png'): 'A', P('x/02_A2.png'): 'A'}
        groups, park = split_groups(paths, cls)
        self.assertEqual(len(groups), 2)

    def test_natural_key(self):
        ordered = sorted([P('x/10.jpg'), P('x/2.jpg'), P('x/1.jpg')], key=natural_key)
        self.assertEqual([p.name for p in ordered], ['1.jpg', '2.jpg', '10.jpg'])

    def test_unique_destination_same_content_skips(self):
        tmp = tempfile.mkdtemp()
        src = P(tmp, 'src.txt'); src.write_bytes(b'hello')
        d1 = unique_destination(tmp, 'dup.txt', src)
        d1.write_bytes(b'hello')
        d2 = unique_destination(tmp, 'dup.txt', src)
        self.assertEqual(d1, d2)

    def test_unique_destination_numbering(self):
        tmp = tempfile.mkdtemp()
        existing = P(tmp, 'dup.txt'); existing.write_bytes(b'one')
        src = P(tmp, 'src.txt'); src.write_bytes(b'two')
        d = unique_destination(tmp, 'dup.txt', src)
        self.assertEqual(d.name, 'dup (1).txt')

    def test_sanitize_stem(self):
        self.assertEqual(sanitize_stem('prohibited<name>'), 'prohibited_name_')
        self.assertEqual(sanitize_stem('CON'), 'CON_')
        self.assertEqual(sanitize_stem('   '), 'фото')


class ClassifyStubTests(unittest.TestCase):
    def test_classify_stub(self):
        from unittest.mock import patch

        import cv2
        import numpy as np
        import photo

        texts = ['A', 'просто фото', 'B', 'ещё фото']
        call = {'i': 0}

        def fake_recognize(frame, cfg, do_ocr=True, orig=None):
            text = texts[call['i']]
            call['i'] += 1
            return [{'number': '', 'raw': text, 'method': 'QR / штрихкод'}]

        paths = [P('x/a.png'), P('x/f1.jpg'), P('x/b.png'), P('x/f2.jpg')]
        from config import worker_config, settings
        cfg = worker_config(settings())
        with patch('recognition.recognize_frame', side_effect=fake_recognize), \
                patch('cv2.imdecode', return_value=np.zeros((10, 10, 3), dtype=np.uint8)), \
                patch('photo.np_from_file', return_value=b''):
            classifications = classify_photos(paths, cfg)
        self.assertEqual(classifications[P('x/a.png')], 'A')
        self.assertEqual(classifications[P('x/b.png')], 'B')
        self.assertIsNone(classifications[P('x/f1.jpg')])
        self.assertIsNone(classifications[P('x/f2.jpg')])


class RegistryTests(unittest.TestCase):
    def test_registry_lifecycle(self):
        tmp = tempfile.mkdtemp()
        reg = PhotoRegistry(Path(tmp) / 'photo.db')
        sid = reg.start_session(OP_COPY, tmp, 1, 2)
        reg.register_ops(sid, [('Товар A', 'A', P('a/x.jpg'), P('out/x.jpg'), OP_COPY),
                               ('Товар A', 'A', P('a/y.jpg'), P('out/y.jpg'), OP_COPY)])
        pend = reg.pending_ops(sid)
        self.assertEqual(len(pend), 2)
        reg.mark_done(pend[0]['id'], 'aaa')
        reg.mark_failed(pend[1]['id'], 'boom')
        pend = reg.pending_ops(sid)
        self.assertEqual(len(pend), 1)
        self.assertEqual(pend[0]['state'], 'failed')
        counts = reg.counts(sid)
        self.assertEqual(counts.get('done'), 1)
        self.assertEqual(counts.get('failed'), 1)
        reg.finish_session(sid)


class ExecutePlanTests(unittest.TestCase):
    def test_copy(self):
        tmp = tempfile.mkdtemp()
        sep = P(tmp, '01_A.jpg'); sep.write_bytes(b'image-data-A')
        member = P(tmp, '02_f1.jpg'); member.write_bytes(b'image-data-B')
        parked = P(tmp, '03_extra.jpg'); parked.write_bytes(b'image-data-C')
        dest_root = P(tmp, 'out')
        reg = PhotoRegistry(P(tmp) / 'photo.db')
        sid = reg.start_session(OP_COPY, dest_root, 1, 3)
        done, failed = execute_plan(
            sid, [Group('A', separator=sep, items=[member])], [(parked, 'До первого разделителя')],
            dest_root, OP_COPY, reg)
        self.assertEqual(done, 3)
        self.assertEqual(failed, 0)
        self.assertTrue((dest_root / 'Товар A' / '01_A.jpg').is_file())
        self.assertTrue((dest_root / 'Товар A' / '02_f1.jpg').is_file())
        self.assertTrue((dest_root / 'Парковка' / '03_extra.jpg').is_file())
        self.assertTrue(sep.is_file())  # источник при копировании не удаляется

    def test_move(self):
        tmp = tempfile.mkdtemp()
        member = P(tmp, '01_move.jpg'); member.write_bytes(b'image-data-move')
        dest_root = P(tmp, 'out')
        reg = PhotoRegistry(P(tmp) / 'photo2.db')
        sid = reg.start_session(OP_MOVE, dest_root, 1, 1)
        done, failed = execute_plan(
            sid, [Group('B', separator=None, items=[member])], [], dest_root, OP_MOVE, reg)
        self.assertEqual(done, 1)
        self.assertEqual(failed, 0)
        self.assertTrue((dest_root / 'Товар B' / '01_move.jpg').is_file())
        self.assertFalse(member.exists())  # источник удалён после проверенной копии

    def test_missing_source_is_failed(self):
        tmp = tempfile.mkdtemp()
        missing = P(tmp, 'неттакого.jpg')
        dest_root = P(tmp, 'out')
        reg = PhotoRegistry(P(tmp) / 'photo3.db')
        sid = reg.start_session(OP_COPY, dest_root, 1, 1)
        done, failed = execute_plan(
            sid, [Group('A', separator=missing, items=[])], [], dest_root, OP_COPY, reg)
        self.assertEqual(done, 0)
        self.assertEqual(failed, 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
